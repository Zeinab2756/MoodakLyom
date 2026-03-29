package com.moodaklyom.data.model

data class Emotion(
    val primary_emotion: String?,
    val confidence: Float?
)

data class TranscriptionResponse(
    val success: Boolean,
    val text: String?
)