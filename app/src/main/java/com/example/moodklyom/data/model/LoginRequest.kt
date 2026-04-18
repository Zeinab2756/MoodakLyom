package com.example.moodklyom.data.model

data class LoginRequest(
    val username: String,
    val password: String,
    val avatar: String? = null,
    val preferences: Map<String, Any>? = null
)
