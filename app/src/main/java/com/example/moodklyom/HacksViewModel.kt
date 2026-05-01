package com.example.moodklyom

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.moodklyom.data.api.RetrofitClient
import com.example.moodklyom.data.local.TokenManager
import com.example.moodklyom.data.model.WellnessTip
import com.example.moodklyom.data.model.TaskCreate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HacksUiState(
    val isLoading: Boolean = true,
    val hacks: List<WellnessTip> = emptyList(),
    val latestMood: String? = null,
    val error: String? = null,
    val creatingTaskIds: Set<Int> = emptySet()
)

class HacksViewModel(private val tokenManager: TokenManager) : ViewModel() {

    private val _uiState = MutableStateFlow(HacksUiState())
    val uiState: StateFlow<HacksUiState> = _uiState.asStateFlow()

    init {
        loadHacks()
    }

    fun refresh() {
        loadHacks()
    }

    private fun loadHacks() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val token = tokenManager.token.first()
                RetrofitClient.setAuthToken(token)

                val response = RetrofitClient.apiService.getWellnessTips()
                val moodsResponse = RetrofitClient.apiService.getAllMoods(limit = 1)

                if (!response.isSuccessful) {
                    val errorBody = response.errorBody()?.string()
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            error = "Failed to load tips: ${errorBody ?: response.code()}"
                        )
                    }
                    return@launch
                }

                val body = response.body()
                if (body != null && body.isNotEmpty()) {
                    val latestMood = if (moodsResponse.isSuccessful) {
                        moodsResponse.body()?.moods?.firstOrNull()?.emotion
                    } else {
                        null
                    }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            hacks = body,
                            latestMood = latestMood,
                            error = null,
                            creatingTaskIds = emptySet()
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            error = "No tips available yet."
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = "Could not load tips: ${e.message}"
                    )
                }
            }
        }
    }

    fun addHackAsTask(hack: WellnessTip, onSuccess: () -> Unit = {}) {
        viewModelScope.launch {
            _uiState.update { it.copy(creatingTaskIds = it.creatingTaskIds + hack.id) }
            try {
                val token = tokenManager.token.first()
                RetrofitClient.setAuthToken(token)

                val response = RetrofitClient.apiService.createTask(
                    TaskCreate(
                        title = hack.title,
                        description = hack.description,
                        priority = "MEDIUM"
                    )
                )

                if (response.isSuccessful && response.body()?.success == true) {
                    _uiState.update { it.copy(creatingTaskIds = it.creatingTaskIds - hack.id) }
                    onSuccess()
                } else {
                    val msg = response.errorBody()?.string() ?: "Failed to add to tasks"
                    _uiState.update {
                        it.copy(
                            error = msg,
                            creatingTaskIds = it.creatingTaskIds - hack.id
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        error = e.message ?: "Failed to add to tasks",
                        creatingTaskIds = it.creatingTaskIds - hack.id
                    )
                }
            }
        }
    }
}
