from rest_framework.exceptions import APIException

class UserAdviceException(APIException):
    status_code = 400
    default_detail = 'One or more data provided is invalid'
    default_code = 'invalid_request_data'

class LimitsExceededException(UserAdviceException):
    status_code = 400
    default_detail = 'Limits exceeded'
    default_code = 'limits_exceeded'

class UnauthorizedException(APIException):
    status_code = 403
    default_detail = 'You are not allowed to perform action on this resource'
    default_code = 'unathorized'


class ValidationException(APIException):
    status_code = 400
    default_detail = 'Invalid or incomplete request data'
    default_code = 'validation_error'

class InvalidOTPException(APIException):
    status_code = 400
    default_detail = 'Invalid OTP provided'
    default_code = 'invalid_login_otp'

class ExpiredOTPException(APIException):
    status_code = 400
    default_detail = 'Expired OTP provided'
    default_code = 'expired_otp'


class InvalidKeyFormat(APIException):
    status_code = 400
    default_detail = 'Invalid key used'
    default_code = 'invalid_settings'


class InvalidAddressException(APIException):
    status_code = 400
    default_detail = 'Invalid zipcode, address or/and country combination'
    default_code = 'invalid_address'


class UniqueAPIRefException(APIException):
    status_code = 400
    default_detail = "Record with similar api_ref already exists"
    default_code = 'invalid_api_ref'


class InvalidPhoneNumber(Exception):
    def __init__(self, message="Invalid phone number provided"):
        self.message = message
        super().__init__(self.message)