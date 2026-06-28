import ast
from django.conf import settings
from django.test import TestCase
from cryptography.fernet import Fernet


def generate_cipher_suite():
    return Fernet(
        settings.CRYPTOGRAPHY_KEY
    )


class EncryptionTests(TestCase):
    def test_encryption_key_present(self):
        '''
        test_encryption_key_present() returns False if CRYPTOGRAPHY_KEY in settings.py hasn't been set in env
        '''
        self.assertIs(
            True if settings.CRYPTOGRAPHY_KEY else False,
            True
        )

    def test_encryption_key_can_encrypt_bytes(self):
        '''
        test_encryption_key_can_encrypt() returns False if CRYPTOGRAPHY_KEY in settings.py cannot encrypt bytes
        '''
        def encryption_case():
            try:
                cipher_suite = generate_cipher_suite()
                cipher_suite.encrypt(
                    str('4242..1234..5678..0123').encode('utf-8')
                )
                return True
            except Exception as e:
                print(self, '-->', e)
            return False

        self.assertIs(
            encryption_case(),
            True
        )

    def test_encryption_key_can_encrypt_bytes_only(self):
        '''
        test_encryption_key_can_encrypt_bytes_only() returns True if CRYPTOGRAPHY_KEY in settings.py can encrypt types other than bytes
        '''
        cipher_suite = generate_cipher_suite()

        def encryption_case_str(cipher_suite):
            try:
                cipher_suite.encrypt(
                    '4242..1234..5678..0123'
                )
                return True
            except Exception as e:
                print(self, '--> str -->', e)
            return False

        def encryption_case_int(cipher_suite):
            try:
                cipher_suite.encrypt(
                    4242123456780123
                )
                return True
            except Exception as e:
                print(self, '--> int -->', e)
            return False

        def encryption_case_list(cipher_suite):
            try:
                cipher_suite.encrypt(
                    []
                )
                return True
            except Exception as e:
                print(self, '--> list -->', e)
            return False

        def encryption_case_dict(cipher_suite):
            try:
                cipher_suite.encrypt(
                    {}
                )
                return True
            except Exception as e:
                print(self, '--> dict -->', e)
            return False

        def encryption_case_none(cipher_suite):
            try:
                cipher_suite.encrypt(
                    None
                )
                return True
            except Exception as e:
                print(self, '--> None -->', e)
            return False

        self.assertIs(
            encryption_case_str(cipher_suite),
            False
        )
        self.assertIs(
            encryption_case_int(cipher_suite),
            False
        )
        self.assertIs(
            encryption_case_list(cipher_suite),
            False
        )
        self.assertIs(
            encryption_case_dict(cipher_suite),
            False
        )
        self.assertIs(
            encryption_case_none(cipher_suite),
            False
        )

    def test_encryption_key_can_decrypt_bytes(self):
        '''
        test_encryption_key_can_decrypt_bytes() returns False if CRYPTOGRAPHY_KEY in settings.py cannot decrypt bytes
        '''
        cipher_suite = generate_cipher_suite()
        def encryption_case(cipher_suite):
            try:
                encrypted = cipher_suite.encrypt(
                    str('4242..1234..5678..0123').encode('utf-8')
                )
                cipher_suite.decrypt(
                    encrypted
                )
                return True
            except Exception as e:
                print(self, '-->', e)
            return False

        def encryption_case_eval_false(cipher_suite):
            try:
                encrypted = cipher_suite.encrypt(
                    str('4242..1234..5678..0123').encode('utf-8')
                )
                cipher_suite.decrypt(
                    str(encrypted)
                )
                return True
            except Exception as e:
                print(self, '--> Eval -->', e)
            return False

        def encryption_case_eval_true(cipher_suite):
            try:
                encrypted = cipher_suite.encrypt(
                    str('4242..1234..5678..0123').encode('utf-8')
                )
                cipher_suite.decrypt(
                    ast.literal_eval(str(encrypted))
                )
                return True
            except Exception as e:
                print(self, '--> Eval -->', e)
            return False

        self.assertIs(
            encryption_case(cipher_suite),
            True
        )
        self.assertIs(
            encryption_case_eval_false(cipher_suite),
            False
        )
        self.assertIs(
            encryption_case_eval_true(cipher_suite),
            True
        )
