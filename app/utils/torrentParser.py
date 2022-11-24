import io
import hashlib
import urllib.parse


class TorrentParser:
    level = -1  # Pretty printing when self.logging
    debug = False
    info_start = 0
    info_end = 0
    info_start_dict = 0
    open_dicts = 0
    file = None

    def log(self, text):
        if self.debug:
            print("  " * (self.level + text))

    @staticmethod
    def isNumeric(i):
        try:
            int(i)
            return True
        except ValueError:
            return False

    def readDict(self, str_data=None):

        self.open_dicts += 1

        self.level += 1

        if str_data is not None:
            if isinstance(str_data, str):
                str_data = str_data.encode("utf-8")
            self.file = io.BytesIO(str_data)

        self.log("readDict at %i" % self.file.tell())
        dictionary = {}
        key = None
        value = None

        c = True
        while c:
            c = self.file.read(1)
            try:
                d = c.decode("utf-8")
            except UnicodeDecodeError:
                continue

            if d == 'd':
                # Recursion!
                newD = self.readDict()
                # Dictionaries can only be values
                if value is None:
                    value = newD

            if d == 'l':
                # List
                self.level += 1
                ll = self.readList()
                # Lists can only be values
                if value is None:
                    value = ll
                self.level -= 1

            if self.isNumeric(d):
                # String
                self.level += 1
                self.file.seek(-1, io.SEEK_CUR)  # Start of the string, ex. 6:foobar
                s = self.readString()
                if key is not None:
                    # If the key is set, this is the value
                    value = s
                else:
                    # If the key isn't set, this is the key
                    key = s
                    if key == "info":
                        # Info data starts here
                        self.info_start_dict = self.open_dicts
                        self.info_start = self.file.tell()
                self.level -= 1

            if d == 'i':
                # Integer
                self.level += 1
                self.file.seek(-1, io.SEEK_CUR)  # Start of the integer, ex. i42e
                i = self.readInt()
                if key is not None:
                    # If the key is set, this is the value
                    value = i
                else:
                    # If the key isn't set, this is the key
                    key = i
                self.level -= 1

            if d == 'e':
                # Dict close
                self.level -= 1
                if self.info_start_dict == self.open_dicts:
                    # Info data ends
                    self.info_end = self.file.tell() - 1
                self.open_dicts -= 1
                break

            # Bencoded files are dictionaries, so we need both key and value
            if key is not None and value is not None:
                dictionary[key] = value
                key = None
                value = None

            if key is None and value is not None and str_data is not None:
                return value

        return dictionary

    def readList(self):
        self.log("readList at %i" % self.file.tell())
        c = True

        list_values = []

        while c:
            c = self.file.read(1)
            try:
                d = c.decode("utf-8")
            except UnicodeDecodeError:
                continue

            if d == 'd':
                newD = self.readDict()
                list_values.append(newD)

            if d == 'l':
                # List
                self.level += 1
                ll = self.readList()

                list_values.append(ll)

                self.level -= 1

            if self.isNumeric(d):
                # String
                self.level += 1
                self.file.seek(-1, io.SEEK_CUR)  # Start of the string, ex. 6:foobar
                s = self.readString()

                list_values.append(s)

                self.level -= 1

            if d == 'i':
                # Integer
                self.level += 1
                self.file.seek(-1, io.SEEK_CUR)  # Start of the integer, ex. i42e
                i = self.readInt()

                list_values.append(i)

                self.level -= 1

            if d == 'e':
                # List end
                self.level -= 1
                break

        return list_values

    @staticmethod
    def _readCharacter(fileObj):
        try:
            return fileObj.read(1).decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Malformed integer: UnicodeDecodeError")

    def readInt(self):
        """
        Ints must be of the form i[0-9]+e or i-[0-9]+e
        """
        self.log("readInt at %i" % self.file.tell())

        # Integers must be encapsulated, ex. i42e = 42

        if not self._readCharacter(self.file) == 'i':
            raise ValueError("Malformed integer - must lead with 'i'")

        num = ""
        while True:
            # We read the file until 'e'
            d = self.file.read(1).decode("utf-8")

            if self.isNumeric(d) or d == '-':
                num += d
            elif d == 'e':
                # Correctly read integer
                break
            else:
                raise ValueError("Malformed integer element - {} + *{}*".format(num, d))

        realInt = int(num)

        self.level += 1
        self.log("Int: %i" % realInt)
        self.level -= 1
        return realInt

    def readString(self):
        self.log("readString at %i" % self.file.tell())
        # Read the length of the string
        b = True
        len_text = ""

        # Read file until non-numeric value
        while b:
            b = self.file.read(1)
            try:
                d = b.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Malformed UTF-8 string")
            if self.isNumeric(d):
                len_text += d
            else:
                break
        # Now we have the length of the string
        str_len = int(len_text)

        # Read the string
        string = self.file.read(str_len)
        try:
            utfString = string.decode("utf-8")
            self.level += 1
            self.log("String: %s" % utfString)
            self.level -= 1
            return utfString
        except UnicodeDecodeError:
            # If we can't decode the string as UTF-8 then it's data
            self.level += 1
            self.log("Data")
            self.level -= 1
            # Return "raw" data
            return string

    def readFile(self, path):

        self.file = open(path, "rb")

        # I think that there can't be multiple dictionaries at root level
        # Correct me if I'm wrong

        dictionary = {}

        # Read torrent file

        c = self.file.read(1)
        while c:
            try:
                d = c.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if d == 'd':
                # Dictionary
                self.open_dicts += 1
                dictionary["torrent"] = self.readDict()
            c = self.file.read(1)

        # Calculate infohash
        #  is an SHA-1 hash of the value of the info key (bencoded dict)

        self.file.seek(self.info_start)
        infohash_data = self.file.read(self.info_end - self.info_start)

        infohash = hashlib.sha1(infohash_data)

        self.file.close()

        # Infohash in a few different formats
        extra = {"infohash": {"digest": infohash.digest(), "hex": infohash.hexdigest(),
                              "url": urllib.parse.quote(infohash.digest())}}

        dictionary["extra_data"] = extra

        return dictionary
