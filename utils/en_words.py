import os


class EnWords:
    INSTANCE = None
    en_words = []

    def __init__(self):
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'corncob_lowercase.txt')
        with open(file_path, 'r') as word_file:
            self.en_words = set(word.strip().lower() for word in word_file)

    @classmethod
    def instance(cls):
        if not cls.INSTANCE:
            cls.INSTANCE = EnWords()
        return cls.INSTANCE

    @classmethod
    def is_en_word(cls, word):
        return word.lower() in cls.instance().en_words
