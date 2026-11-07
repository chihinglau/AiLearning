import java.io.File
import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// 发版号规则（与 docs/skills.md §5.3 一致，双端必须相同）：
//   versionCode = major * 10000 + minor * 100 + patch * 10 + build
//   例：pubspec `version: 1.0.0+1` → versionCode 10001
// 鸿蒙 `AppScope/app.json5` 由 scripts\sync-version.ps1 写入同一值。
fun releaseVersionCode(versionName: String?, buildNumber: Int?): Int {
    val segments = (versionName ?: "0.0.0").split(".")
    val major = segments.getOrNull(0)?.toIntOrNull() ?: 0
    val minor = segments.getOrNull(1)?.toIntOrNull() ?: 0
    val patch = segments.getOrNull(2)?.toIntOrNull() ?: 0
    return major * 10000 + minor * 100 + patch * 10 + (buildNumber ?: 0)
}

val keystoreProperties = Properties()
// rootProject 是 app/android；keystore.properties 由 scripts\make-release-keystore.ps1
// 写在仓库根目录（app/android/../..）。
val repoRoot = rootProject.projectDir.parentFile.parentFile
val keystorePropertiesFile = File(repoRoot, "keystore.properties")
val releaseRequested =
    gradle.startParameter.taskNames.any { it.contains("release", ignoreCase = true) }
if (keystorePropertiesFile.exists()) {
    FileInputStream(keystorePropertiesFile).use { keystoreProperties.load(it) }
}

android {
    namespace = "com.ailearning.ai_learning"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            create("release") {
                fun required(name: String): String =
                    keystoreProperties.getProperty(name)
                        ?: throw GradleException(
                            "keystore.properties 缺少 $name；请重新运行 scripts\\make-release-keystore.ps1"
                        )
                keyAlias = required("keyAlias")
                keyPassword = required("keyPassword")
                storePassword = required("storePassword")
                val store = file(required("storeFile"))
                if (!store.exists()) {
                    throw GradleException(
                        "keystore.properties 指向的签名文件不存在：$store；请重新运行 scripts\\make-release-keystore.ps1"
                    )
                }
                storeFile = store
            }
        } else if (releaseRequested) {
            throw GradleException(
                "缺少 keystore.properties，release 构建禁止回退 debug 签名。" +
                    "请先运行 scripts\\make-release-keystore.ps1（正式签名须备份并纳入密钥管理）。"
            )
        }
    }

    defaultConfig {
        applicationId = "com.ailearning.ai_learning"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = releaseVersionCode(flutter.versionName, flutter.versionCode)
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.findByName("release")
        }
    }
}

// integration_test 默认引入 espresso 3.2.0；在 AGP 8 下 espresso-core 与
// espresso-idling-resource 共用 androidx.test.espresso 命名空间会触发
// Manifest 合并校验失败，这里统一升级到 3.5.1（已拆分命名空间）。
configurations.all {
    resolutionStrategy {
        force("androidx.test.espresso:espresso-core:3.5.1")
        force("androidx.test.espresso:espresso-idling-resource:3.5.1")
        force("androidx.test:core:1.5.0")
        force("androidx.test:runner:1.5.2")
        force("androidx.test:rules:1.5.0")
        force("androidx.test.ext:junit:1.1.5")
    }
}

flutter {
    source = "../.."
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}
