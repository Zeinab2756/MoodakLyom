package com.example.moodklyom

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.moodklyom.data.api.RetrofitClient
import com.example.moodklyom.data.local.TokenManager
import com.example.moodklyom.data.model.LoginRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class LoginUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
    val token: String? = null
)

class LoginViewModel(private val tokenManager: TokenManager) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun login(username: String, password: String, onSuccess: (String) -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null, success = false)

            try {
                val response = RetrofitClient.apiService.loginOrSignup(
                    LoginRequest(
                        username = username,
                        password = password
                    )
                )

                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    if (body.success && body.data != null) {

                        val token = body.data.token

                        // ⭐ Save token + userId + username
                        tokenManager.saveToken(
                            token = token,
                            userId = body.data.user.id,
                            username = body.data.user.username
                        )



                        // Set token for API
                        RetrofitClient.setAuthToken(token)

                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            success = true,
                            error = null,
                            token = token
                        )
                        onSuccess(token)

                    } else {
                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            error = body.error?.message ?: "Unknown error"
                        )
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Network error"
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "Failed: $errorBody"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Exception: ${e.message}"
                )
            }
        }
    }
}
