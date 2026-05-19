package com.aliothmoon.maameow.remote.internal

import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.os.Build
import android.view.Surface
import com.aliothmoon.maameow.bridge.NativeBridgeLib
import com.aliothmoon.maameow.constant.AndroidVersions
import com.aliothmoon.maameow.constant.DefaultDisplayConfig
import com.aliothmoon.maameow.constant.DefaultDisplayConfig.VD_NAME
import com.aliothmoon.maameow.third.Ln
import com.aliothmoon.maameow.third.wrappers.ServiceManager
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference


object VirtualDisplayManager {

    private const val STATE_COLD = 0
    private const val STATE_HOT = 1

    private const val VIRTUAL_DISPLAY_FLAG_PUBLIC: Int = DisplayManager.VIRTUAL_DISPLAY_FLAG_PUBLIC
    private const val VIRTUAL_DISPLAY_FLAG_PRESENTATION: Int =
        DisplayManager.VIRTUAL_DISPLAY_FLAG_PRESENTATION
    private const val VIRTUAL_DISPLAY_FLAG_OWN_CONTENT_ONLY: Int =
        DisplayManager.VIRTUAL_DISPLAY_FLAG_OWN_CONTENT_ONLY
    private const val VIRTUAL_DISPLAY_FLAG_SUPPORTS_TOUCH: Int = 1 shl 6
    private const val VIRTUAL_DISPLAY_FLAG_ROTATES_WITH_CONTENT: Int = 1 shl 7
    private const val VIRTUAL_DISPLAY_FLAG_DESTROY_CONTENT_ON_REMOVAL: Int = 1 shl 8
    private const val VIRTUAL_DISPLAY_FLAG_SHOULD_SHOW_SYSTEM_DECORATIONS: Int = 1 shl 9
    private const val VIRTUAL_DISPLAY_FLAG_TRUSTED: Int = 1 shl 10
    private const val VIRTUAL_DISPLAY_FLAG_OWN_DISPLAY_GROUP: Int = 1 shl 11
    private const val VIRTUAL_DISPLAY_FLAG_ALWAYS_UNLOCKED: Int = 1 shl 12
    private const val VIRTUAL_DISPLAY_FLAG_TOUCH_FEEDBACK_DISABLED: Int = 1 shl 13
    private const val VIRTUAL_DISPLAY_FLAG_OWN_FOCUS: Int = 1 shl 14
    private const val VIRTUAL_DISPLAY_FLAG_DEVICE_DISPLAY_GROUP: Int = 1 shl 15
    private const val VIRTUAL_DISPLAY_FLAG_STEAL_TOP_FOCUS_DISABLED: Int = 1 shl 16

    private const val VD_SYSTEM_DECORATIONS = false
    private const val VD_DESTROY_CONTENT = true

    const val DISPLAY_NONE = -1

    data class DisplayConfig(
        val width: Int = DefaultDisplayConfig.WIDTH,
        val height: Int = DefaultDisplayConfig.HEIGHT,
        val dpi: Int = DefaultDisplayConfig.DPI
    )

    private val state = AtomicInteger(STATE_COLD)
    private val config = AtomicReference(DisplayConfig())
    private val displayId = AtomicInteger(DISPLAY_NONE)
    private val virtualDisplay = AtomicReference<VirtualDisplay?>()

    private val monitorSurface = AtomicReference<Surface?>()

    fun setMonitorSurface(surface: Surface?) {
        val old = monitorSurface.getAndSet(surface)
        if (old != null && old != surface) {
            old.release()
            Ln.i("Old monitor surface released")
        }
        Ln.i("setMonitorSurface: old=${old != null}, new=${surface != null}")
    }

    /**
     * 幂等：COLD 时建 VD + AImageReader，HOT 时直接返回当前 displayId。
     * VD 与 AImageReader 在 HOT 状态下常驻，由 release() 显式释放。
     */
    fun start(): Int {
        if (state.get() == STATE_HOT) {
            return displayId.get()
        }
        if (!state.compareAndSet(STATE_COLD, STATE_HOT)) {
            return displayId.get()
        }
        return try {
            val cfg = config.get()
            val surface = NativeBridgeLib.setupNativeCapturer(cfg.width, cfg.height)
            createVirtualDisplay(surface, cfg)
            Ln.i("VirtualDisplayManager started, displayId=${displayId.get()}")
            displayId.get()
        } catch (e: Exception) {
            Ln.e("VirtualDisplayManager start failed", e)
            releaseInternal()
            state.set(STATE_COLD)
            DISPLAY_NONE
        }
    }

    /**
     * 硬释放：销毁 VD + AImageReader + monitorSurface，回到 COLD。
     * 仅由模式切换 PRIMARY、分辨率变化、紧急清理、进程退出路径调用。
     */
    fun release() {
        if (!state.compareAndSet(STATE_HOT, STATE_COLD)) {
            return
        }
        releaseInternal()
        monitorSurface.getAndSet(null)?.release()
        Ln.i("VirtualDisplayManager released")
    }

    /**
     * 仅记录新分辨率：变化且当前 HOT 时直接 release，让下一次 start() 用新 config 重建；
     * COLD 时仅更新 config 不释放。
     * 调用方必须保证：setResolution 之后再调 start()，不能复用之前的 displayId。
     */
    fun setResolution(width: Int, height: Int, dpi: Int = config.get().dpi) {
        val newConfig = DisplayConfig(width, height, dpi)
        val oldConfig = config.getAndSet(newConfig)
        if (oldConfig == newConfig) return
        Ln.i("Resolution changed: ${oldConfig.width}x${oldConfig.height} -> ${width}x${height}")
        if (state.get() == STATE_HOT) {
            release()
        }
    }

    fun getDisplayId(): Int = displayId.get()

    private fun releaseInternal() {
        virtualDisplay.getAndSet(null)?.release()
        NativeBridgeLib.releaseNativeCapturer()
        displayId.set(DISPLAY_NONE)
    }

    private fun createVirtualDisplay(surface: Surface, cfg: DisplayConfig) {
        val flags = buildDisplayFlags()
        val wm = ServiceManager.getWindowManager()
        val physicalRotation = runCatching { wm.rotation }.getOrDefault(-1)
        Ln.i("Physical display rotation: $physicalRotation")

        val vd = ServiceManager.getDisplayManager()
            .createNewVirtualDisplay(
                VD_NAME,
                cfg.width,
                cfg.height,
                cfg.dpi,
                surface,
                flags
            )
        virtualDisplay.set(vd)
        val vdId = vd.display.displayId
        displayId.set(vdId)

        val d = vd.display
        Ln.i(
            "VD created: id=$vdId" +
            ", configured=${cfg.width}x${cfg.height}" +
            ", actual=${d.width}x${d.height}" +
            ", rotation=${d.rotation}" +
            ", flags=0x${flags.toString(16)}"
        )

        if (d.rotation != Surface.ROTATION_0) {
            // 所有旋转非零的情况都先尝试 freezeRotation
            runCatching {
                wm.freezeRotation(vdId, Surface.ROTATION_0)
                Ln.i("freezeRotation done, post-freeze rotation=${vd.display.rotation}")
            }.onFailure { e -> Ln.w("freezeRotation failed: ${e.message}") }

            if (physicalRotation == Surface.ROTATION_0) {
                // 物理屏处于自然方向（rotation=0）而 VD 却有旋转角，
                // 这是横屏原生设备如AYN Odin2的典型特征：
                // 此类设备的定制 ROM 对二级显示调 freezeRotation 无效，
                // 额外调 setForcedDisplaySize 强制 VD 向内部 app 上报横屏尺寸。
                Ln.w(
                    "Landscape-native device detected (physRot=0, vdRot=${d.rotation}), " +
                    "applying setForcedDisplaySize"
                )
                runCatching {
                    wm.setForcedDisplaySize(vdId, cfg.width, cfg.height)
                    Ln.i("setForcedDisplaySize(${cfg.width}x${cfg.height}) applied")
                }.onFailure { e -> Ln.w("setForcedDisplaySize failed: ${e.message}") }
            }
        }
    }

    private fun buildDisplayFlags(): Int {
        var flags = (VIRTUAL_DISPLAY_FLAG_PUBLIC
                or VIRTUAL_DISPLAY_FLAG_PRESENTATION
                or VIRTUAL_DISPLAY_FLAG_OWN_CONTENT_ONLY
                or VIRTUAL_DISPLAY_FLAG_SUPPORTS_TOUCH)

        if (VD_DESTROY_CONTENT) {
            flags = flags or VIRTUAL_DISPLAY_FLAG_DESTROY_CONTENT_ON_REMOVAL
        }
        if (VD_SYSTEM_DECORATIONS) {
            flags = flags or VIRTUAL_DISPLAY_FLAG_SHOULD_SHOW_SYSTEM_DECORATIONS
        }
        if (Build.VERSION.SDK_INT >= AndroidVersions.API_33_ANDROID_13) {
            flags = flags or (VIRTUAL_DISPLAY_FLAG_TRUSTED
                    or VIRTUAL_DISPLAY_FLAG_OWN_DISPLAY_GROUP
                    or VIRTUAL_DISPLAY_FLAG_ALWAYS_UNLOCKED
                    or VIRTUAL_DISPLAY_FLAG_TOUCH_FEEDBACK_DISABLED)
            if (Build.VERSION.SDK_INT >= AndroidVersions.API_34_ANDROID_14) {
                flags = flags or (VIRTUAL_DISPLAY_FLAG_OWN_FOCUS
                        or VIRTUAL_DISPLAY_FLAG_DEVICE_DISPLAY_GROUP
                        or VIRTUAL_DISPLAY_FLAG_STEAL_TOP_FOCUS_DISABLED)
            }
        }
        return flags
    }
}
