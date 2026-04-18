package com.example.moodklyom.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.moodklyom.data.api.RetrofitClient
import com.example.moodklyom.data.local.TokenManager
import com.example.moodklyom.data.model.TaskCreate
import com.example.moodklyom.ui.components.CustomTopAppBar
import com.example.moodklyom.ui.theme.MintPrimary
import com.example.moodklyom.ui.theme.White
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@Composable
fun AddTaskScreen(navController: NavController) {
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var selectedPriority by remember { mutableStateOf("MEDIUM") }
    var isSaving by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val priorities = listOf("LOW", "MEDIUM", "HIGH", "URGENT")
    val context = LocalContext.current
    val tokenManager = remember { TokenManager(context) }
    val scope = rememberCoroutineScope()

    Column(modifier = Modifier.fillMaxSize()) {
        CustomTopAppBar(
            title = "Add Task",
            onBackClick = { navController.popBackStack() }
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("Task Title") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("Description (optional)") },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp),
                maxLines = 5
            )

            Text(
                "Priority",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                priorities.forEach { priority ->
                    val isSelected = selectedPriority == priority
                    Button(
                        onClick = { selectedPriority = priority },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isSelected) MintPrimary else MaterialTheme.colorScheme.surface,
                            contentColor = if (isSelected) White else MaterialTheme.colorScheme.onSurface
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            priority,
                            style = MaterialTheme.typography.labelMedium
                        )
                    }
                }
            }

            errorMessage?.let { msg ->
                Text(
                    text = msg,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            Button(
                onClick = {
                    scope.launch {
                        try {
                            isSaving = true
                            errorMessage = null

                            val token = tokenManager.token.first()
                            RetrofitClient.setAuthToken(token)

                            val request = TaskCreate(
                                title = title,
                                description = description.ifBlank { null },
                                priority = selectedPriority
                            )

                            val response = RetrofitClient.apiService.createTask(request)
                            if (response.isSuccessful && response.body()?.success == true) {
                                navController.popBackStack()
                            } else {
                                val msg =
                                    response.errorBody()?.string() ?: "Failed to create task."
                                errorMessage = msg
                            }
                        } catch (e: Exception) {
                            errorMessage = e.message ?: "Failed to create task."
                        } finally {
                            isSaving = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                enabled = title.isNotBlank() && !isSaving,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MintPrimary,
                    contentColor = White
                ),
                shape = RoundedCornerShape(16.dp)
            ) {
                if (isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = White,
                        strokeWidth = 2.dp
                    )
                } else {
                    Text("Save Task", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
