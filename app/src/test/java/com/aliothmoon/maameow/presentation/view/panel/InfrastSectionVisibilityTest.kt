package com.aliothmoon.maameow.presentation.view.panel

import com.aliothmoon.maameow.data.model.InfrastConfig
import com.aliothmoon.maameow.domain.enums.InfrastMode
import com.aliothmoon.maameow.domain.enums.InfrastRotationStyle
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class InfrastSectionVisibilityTest {
    @Test fun stationPresetUsesRoomsAndShowsMoodThreshold() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation,
            rotationStyle = InfrastRotationStyle.StationPreset,
        )
        assertTrue(config.usesRotationStationPreset())
        assertFalse(showFacilities(config))
        assertTrue(showDormThreshold(config))
    }

    @Test fun otherModesKeepExistingVisibility() {
        assertTrue(showFacilities(InfrastConfig(mode = InfrastMode.Normal)))
        assertTrue(showDormThreshold(InfrastConfig(mode = InfrastMode.Normal)))
        assertTrue(showFacilities(InfrastConfig(mode = InfrastMode.Custom)))
        assertTrue(showDormThreshold(InfrastConfig(mode = InfrastMode.Custom)))
        val game = InfrastConfig(mode = InfrastMode.Rotation, rotationStyle = InfrastRotationStyle.Game)
        assertTrue(showFacilities(game))
        assertFalse(showDormThreshold(game))
    }
}
