from fastapi import APIRouter, HTTPException
from app.schemas.emotion_schemas import EmotionRequest, EmotionResponse
from app.services.text_emotion import predict_text_emotion_async

router = APIRouter(prefix="/emotion", tags=["emotion"])


@router.post("/analyze", response_model=EmotionResponse)
async def analyze_emotion(request: EmotionRequest):
    """
    Analyze emotion from user text using fine-tuned BERT.
    """
    try:
        result = await predict_text_emotion_async(request.text)

        return EmotionResponse(
            primary_emotion=result.label,
            confidence=result.confidence,
            alternative_emotions=[
                {"emotion": label, "probability": probability}
                for label, probability in sorted(
                    result.distribution.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:3]
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing emotion: {str(e)}",
        )


@router.get("/health")
async def emotion_health_check():
    """
    Simple health check: run a test prediction and return it.
    """
    test_text = "I am very happy today!"
    result = await predict_text_emotion_async(test_text)
    return {
        "status": "ok",
        "sample_text": test_text,
        "prediction": result.model_dump(),
    }
