package com.aliothmoon.maameow.data.model

import com.aliothmoon.maameow.domain.enums.InfrastMode
import com.aliothmoon.maameow.domain.enums.InfrastRotationStyle
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Base-wide collection is independent from station presets, drones and shard replenishment. */
class BaseRewardCollectionParamsTest {
    private fun collectionEnabled(config: InfrastConfig): Boolean {
        val params = config.toTaskParams(testTaskParamContext()).single().params
        return Json.parseToJsonElement(params).jsonObject.getValue("collect").jsonPrimitive.boolean
    }

    @Test
    fun defaultsEnabledForLegacyProfilesWithoutSavedToggle() {
        assertTrue(collectionEnabled(InfrastConfig()))
        val legacy = com.aliothmoon.maameow.utils.JsonUtils.common
            .decodeFromString<InfrastConfig>("{}")
        assertTrue(legacy.collectBaseRewards)
        assertTrue(collectionEnabled(legacy))
    }

    @Test
    fun allOtherOptionalOperationsCanBeDisabledWithoutDisablingCollection() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation,
            rotationStyle = InfrastRotationStyle.StationPreset,
            presetSelectedRooms = emptyList(),
            presetRest = false,
            stationPresetDrones = StationPresetDrones(enable = false),
            originiumShardAutoReplenishment = false,
            fiammettaRecoveryEnabled = false,
            dormTrustEnabled = false,
            dormFilterNotStationedEnabled = false,
            continueTraining = false,
            receptionMessageBoard = false,
            receptionReceiveClue = false,
            receptionClueExchange = false,
            receptionSendClue = false,
            collectBaseRewards = true,
        )
        assertTrue(collectionEnabled(config))
        assertFalse(collectionEnabled(config.copy(collectBaseRewards = false)))
    }

    @Test
    fun collectionSwitchIsSerializedForEveryMode() {
        for (mode in InfrastMode.entries) {
            assertTrue(collectionEnabled(InfrastConfig(mode = mode, collectBaseRewards = true)))
            assertFalse(collectionEnabled(InfrastConfig(mode = mode, collectBaseRewards = false)))
        }
    }
}
