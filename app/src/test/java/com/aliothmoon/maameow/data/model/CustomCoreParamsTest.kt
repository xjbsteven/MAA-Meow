package com.aliothmoon.maameow.data.model

import com.aliothmoon.maameow.domain.enums.InfrastMode
import com.aliothmoon.maameow.domain.enums.InfrastRotationStyle
import com.aliothmoon.maameow.utils.JsonUtils
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CustomCoreParamsTest {
    private fun params(config: TaskParamProvider) =
        Json.parseToJsonElement(config.toTaskParams(testTaskParamContext()).single().params).jsonObject

    @Test fun recruitMinimumAndReserveAreIndependent() {
        val config = RecruitConfig(
            maxRecruitTimes = 4, minimumRecruitTimesEnabled = true, minimumRecruitTimes = 7,
            level3PermitReserveEnabled = true, level3PermitReserve = 8,
            preserveTagEnabled = true,
        )
        val result = params(config)
        assertEquals(4, result.getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(8, result.getValue("level3_recruitment_permit_reserve").jsonPrimitive.int)
        assertTrue(result.getValue("preserve_tags").jsonArray.isNotEmpty())
        assertEquals(0, params(config.copy(maxRecruitTimes = 0)).getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(0, params(config.copy(minimumRecruitTimesEnabled = false)).getValue("minimum_recruit_times").jsonPrimitive.int)
    }

    @Test fun legacyRecruitFlagMigratesBeforeDecode() {
        val json = JsonUtils.common
        val legacy = """{"forceConfirmToMeetTimes":true,"maxRecruitTimes":4}"""
        val migrated = json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate(legacy, json))
        assertTrue(migrated.minimumRecruitTimesEnabled)
        assertEquals(4, migrated.minimumRecruitTimes)
        assertFalse(json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate("""{"forceConfirmToMeetTimes":false}""", json)).minimumRecruitTimesEnabled)
        val newConfig = """{"forceConfirmToMeetTimes":true,"minimumRecruitTimesEnabled":false,"minimumRecruitTimes":2}"""
        assertFalse(json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate(newConfig, json)).minimumRecruitTimesEnabled)
        assertEquals(migrated, json.decodeFromString<RecruitConfig>(json.encodeToString(RecruitConfig.serializer(), migrated)))
    }

    @Test fun stationPresetKeepsAuxiliaryAndFiammetta() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation, rotationStyle = InfrastRotationStyle.StationPreset,
            presetSelectedRooms = listOf("Control", "Mfg1", "Trade1"), presetRest = false,
            stationPresetDrones = StationPresetDrones(true, StationPresetDrones.Room.Trading, 1, StationPresetDrones.Order.Post),
            fiammettaRecoveryEnabled = true, fiammettaTargets = listOf("清流", "可露希尔"),
            receptionReceiveClue = false, receptionMessageBoard = true,
            dormTrustEnabled = true, dormFilterNotStationedEnabled = false,
        )
        val result = params(config)
        assertEquals("station_preset", result.getValue("rotation_style").jsonPrimitive.content)
        assertEquals(listOf("Control", "Mfg1", "Trade1"), result.getValue("preset").jsonObject.getValue("rooms").jsonArray.map { it.jsonPrimitive.content })
        assertFalse(result.getValue("preset").jsonObject.getValue("rest").jsonPrimitive.boolean)
        assertEquals("post", result.getValue("drones").jsonObject.getValue("order").jsonPrimitive.content)
        assertTrue(result.getValue("fiammetta_recovery_enabled").jsonPrimitive.boolean)
        assertFalse(result.getValue("reception_receive_clue").jsonPrimitive.boolean)
        assertFalse(result.getValue("dorm_notstationed_enabled").jsonPrimitive.boolean)
    }
    @Test fun stationPresetAuxiliaryFlagsAndLayoutSync() {
        val initial = InfrastConfig(
            mode = InfrastMode.Rotation, rotationStyle = InfrastRotationStyle.StationPreset,
            presetRest = true, stationPresetDrones = StationPresetDrones(
                true, StationPresetDrones.Room.Manufacture, 2, StationPresetDrones.Order.Pre,
            ),
            receptionMessageBoard = false, receptionClueExchange = false,
            receptionSendClue = false, originiumShardAutoReplenishment = false,
            dormTrustEnabled = false,
        )
        val result = params(initial)
        assertTrue(result.getValue("preset").jsonObject.getValue("rest").jsonPrimitive.boolean)
        assertEquals("manufacture", result.getValue("drones").jsonObject.getValue("room").jsonPrimitive.content)
        assertEquals(2, result.getValue("drones").jsonObject.getValue("index").jsonPrimitive.int)
        assertEquals("pre", result.getValue("drones").jsonObject.getValue("order").jsonPrimitive.content)
        listOf("reception_message_board", "reception_clue_exchange", "reception_send_clue", "replenish", "dorm_trust_enabled")
            .forEach { assertFalse(it, result.getValue(it).jsonPrimitive.boolean) }
        val reduced = initial.copy(presetLayout = StationPresetLayout(mfgCount = 1), presetSelectedRooms = listOf("Control", "Mfg2"))
            .syncPresetRoomsAfterLayoutChange()
        assertEquals(listOf("Control"), reduced.presetSelectedRooms)
        assertEquals(1, reduced.stationPresetDrones.index)
        assertTrue(initial.copy(presetSelectedRooms = emptyList()).syncPresetRoomsAfterLayoutChange().presetSelectedRooms.isEmpty())
    }

    @Test fun recruitMinimumClampsPersistedValues() {
        val migrated = RecruitConfig(maxRecruitTimes = 2, minimumRecruitTimesEnabled = true, minimumRecruitTimes = 4).migrate()
        assertEquals(2, migrated.minimumRecruitTimes)
        assertEquals(2, params(migrated).getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(1, RecruitConfig(maxRecruitTimes = 0, minimumRecruitTimes = 4).migrate().minimumRecruitTimes)
    }
}
