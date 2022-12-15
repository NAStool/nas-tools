# -*- coding: utf-8 -*-
import sys
import traceback


class ExceptionUtils:
    @classmethod
    def exception_traceback(cls, e):
        print(f"\nException: {e}\nCallstack:\n{''.join(traceback.format_stack()[:-1])}\n{traceback.format_exc()}\n")
