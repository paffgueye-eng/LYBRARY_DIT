from pydantic import BaseModel, Field, field_validator


class BookRecommendation(BaseModel):
    id: int
    title: str
    author: str
    category: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    cover_url: str | None = None


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: list[BookRecommendation]
    model_version: str | None = None


class TrainResponse(BaseModel):
    status: str = "success"
    message: str
    books_count: int = 0
    loans_count: int = 0


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database: str


class SimilarBooksResponse(BaseModel):
    book_id: int
    recommendations: list[BookRecommendation]


class TrainRequest(BaseModel):
    min_df: int = Field(default=1, ge=1, le=10)
    max_features: int = Field(default=5000, ge=100, le=50000)

    @field_validator("max_features")
    @classmethod
    def validate_features(cls, v: int) -> int:
        return v
