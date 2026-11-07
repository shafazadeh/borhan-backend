# src/contract_guard/infrastructure/web/schemas.py

- MobileRequest · class · L8-L17 — class MobileRequest(BaseModel)
- validate_mobile · method · L13-L17 — def validate_mobile(cls, value)
- VerifyRequest · class · L20-L21 — class VerifyRequest(MobileRequest)
- ProfileUpdate · class · L24-L33 — class ProfileUpdate(BaseModel)
- validate_email · method · L30-L33 — def validate_email(cls, value)
- RefreshRequest · class · L36-L37 — class RefreshRequest(BaseModel)
- UserResponse · class · L40-L44 — class UserResponse(BaseModel)
- TokensResponse · class · L47-L52 — class TokensResponse(BaseModel)
- LoginResponse · class · L55-L56 — class LoginResponse(TokensResponse)
