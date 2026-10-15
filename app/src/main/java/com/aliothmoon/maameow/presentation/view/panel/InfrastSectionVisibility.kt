package com.aliothmoon.maameow.presentation.view.panel

import com.aliothmoon.maameow.data.model.InfrastConfig
import com.aliothmoon.maameow.domain.enums.InfrastMode

internal fun showFacilities(config: InfrastConfig): Boolean =
    !config.usesRotationStationPreset()

internal fun showDormThreshold(config: InfrastConfig): Boolean =
    config.mode != InfrastMode.Rotation || config.usesRotationStationPreset()

internal fun showDormAuxiliaryOptions(config: InfrastConfig): Boolean =
    config.mode != InfrastMode.Rotation || config.usesRotationStationPreset()
