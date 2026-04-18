package com.example.moodklyom

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.compose.rememberNavController
import com.example.moodklyom.data.api.RetrofitClient
import com.example.moodklyom.navigation.NavGraph
import com.example.moodklyom.ui.theme.MoodakLyomTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // ⭐ Install Splash Screen before super.onCreate()
        installSplashScreen()

        super.onCreate(savedInstanceState)

        setContent {

            // ⭐ Global theme state (persists on rotation and UI recomposition)
            var isDarkTheme by rememberSaveable { mutableStateOf(false) }

            MoodakLyomTheme(darkTheme = isDarkTheme) {

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()

                    // Initialize retrofit — behavior unchanged
                    RetrofitClient.setAuthToken(null)

                    // ⭐ Pass theme state to NavGraph
                    NavGraph(
                        navController = navController,
                        isDarkTheme = isDarkTheme,
                        onDarkThemeChange = { isDarkTheme = it }
                    )
                }
            }
        }
    }
}
