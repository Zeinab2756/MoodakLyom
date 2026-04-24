package com.example.moodklyom.data.model

import com.google.gson.annotations.SerializedName

data class MoodAnalysisResponse(
    val mood: String,
    val confidence: Double,
    val distribution: Map<String, Double> = emptyMap(),
    val transcript: String? = null,
    @SerializedName("text_emotion")
    val textEmotion: EmotionDistribution? = null,
    @SerializedName("acoustic_emotion")
    val acousticEmotion: EmotionDistribution? = null,
    @SerializedName("sarcasm_suspected")
    val sarcasmSuspected: Boolean = false,
    val language: String? = null,
    @SerializedName("processing_ms")
    val processingMs: Int,
    val degraded: Boolean = false,
    val warnings: List<String> = emptyList(),
)

data class EmotionDistribution(
    val label: String,
    val confidence: Double,
    val distribution: Map<String, Double> = emptyMap(),
    val source: String = "unknown",
)
