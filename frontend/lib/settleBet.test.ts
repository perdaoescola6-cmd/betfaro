/**
 * Unit tests for settleBet function
 * Run with: npx jest lib/settleBet.test.ts
 */

import { settleBet, FixtureData } from './settleBet'

// Helper to create fixture data
function createFixture(
  status: string,
  homeGoals: number | null,
  awayGoals: number | null,
  htHome?: number | null,
  htAway?: number | null,
  cornersTotal?: number | null
): FixtureData {
  return {
    status: { short: status },
    goals: { home: homeGoals, away: awayGoals },
    score: htHome !== undefined ? {
      halftime: { home: htHome, away: htAway ?? null }
    } : undefined,
    corners: cornersTotal !== undefined ? {
      home: null,
      away: null,
      total: cornersTotal
    } : undefined
  }
}

describe('settleBet', () => {
  describe('Game Status Handling', () => {
    test('returns pending for not started games', () => {
      const fixture = createFixture('NS', null, null)
      expect(settleBet('over_2_5_ft', fixture)).toBe('pending')
    })

    test('returns pending for live games', () => {
      const fixture = createFixture('1H', 1, 0)
      expect(settleBet('over_2_5_ft', fixture)).toBe('pending')
    })

    test('returns pending for halftime', () => {
      const fixture = createFixture('HT', 1, 1)
      expect(settleBet('over_2_5_ft', fixture)).toBe('pending')
    })

    test('returns void for cancelled games', () => {
      const fixture = createFixture('CANC', null, null)
      expect(settleBet('over_2_5_ft', fixture)).toBe('void')
    })

    test('returns void for postponed games', () => {
      const fixture = createFixture('PST', null, null)
      expect(settleBet('over_2_5_ft', fixture)).toBe('void')
    })

    test('returns void for abandoned games', () => {
      const fixture = createFixture('ABD', 1, 0)
      expect(settleBet('over_2_5_ft', fixture)).toBe('void')
    })

    test('accepts FT as final', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('over_2_5_ft', fixture)).toBe('won')
    })

    test('accepts AET as final', () => {
      const fixture = createFixture('AET', 3, 2)
      expect(settleBet('over_2_5_ft', fixture)).toBe('won')
    })

    test('accepts PEN as final', () => {
      const fixture = createFixture('PEN', 1, 1)
      expect(settleBet('over_2_5_ft', fixture)).toBe('lost')
    })
  })

  describe('Over FT Goals', () => {
    test('over_0_5_ft: won with 1 goal', () => {
      const fixture = createFixture('FT', 1, 0)
      expect(settleBet('over_0_5_ft', fixture)).toBe('won')
    })

    test('over_0_5_ft: lost with 0 goals', () => {
      const fixture = createFixture('FT', 0, 0)
      expect(settleBet('over_0_5_ft', fixture)).toBe('lost')
    })

    test('over_1_5_ft: won with 2 goals', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('over_1_5_ft', fixture)).toBe('won')
    })

    test('over_1_5_ft: lost with 1 goal', () => {
      const fixture = createFixture('FT', 1, 0)
      expect(settleBet('over_1_5_ft', fixture)).toBe('lost')
    })

    test('over_2_5_ft: won with 3 goals', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('over_2_5_ft', fixture)).toBe('won')
    })

    test('over_2_5_ft: lost with 2 goals', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('over_2_5_ft', fixture)).toBe('lost')
    })

    test('over_3_5_ft: won with 4 goals', () => {
      const fixture = createFixture('FT', 3, 1)
      expect(settleBet('over_3_5_ft', fixture)).toBe('won')
    })

    test('over_3_5_ft: lost with 3 goals', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('over_3_5_ft', fixture)).toBe('lost')
    })
  })

  describe('Under FT Goals', () => {
    test('under_0_5_ft: won with 0 goals', () => {
      const fixture = createFixture('FT', 0, 0)
      expect(settleBet('under_0_5_ft', fixture)).toBe('won')
    })

    test('under_0_5_ft: lost with 1 goal', () => {
      const fixture = createFixture('FT', 1, 0)
      expect(settleBet('under_0_5_ft', fixture)).toBe('lost')
    })

    test('under_1_5_ft: won with 1 goal', () => {
      const fixture = createFixture('FT', 1, 0)
      expect(settleBet('under_1_5_ft', fixture)).toBe('won')
    })

    test('under_1_5_ft: lost with 2 goals', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('under_1_5_ft', fixture)).toBe('lost')
    })

    test('under_2_5_ft: won with 2 goals', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('under_2_5_ft', fixture)).toBe('won')
    })

    test('under_2_5_ft: lost with 3 goals', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('under_2_5_ft', fixture)).toBe('lost')
    })

    test('under_3_5_ft: won with 3 goals', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('under_3_5_ft', fixture)).toBe('won')
    })

    test('under_3_5_ft: lost with 4 goals', () => {
      const fixture = createFixture('FT', 3, 1)
      expect(settleBet('under_3_5_ft', fixture)).toBe('lost')
    })
  })

  describe('BTTS', () => {
    test('btts_yes_ft: won when both teams score', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('btts_yes_ft', fixture)).toBe('won')
    })

    test('btts_yes_ft: lost when only home scores', () => {
      const fixture = createFixture('FT', 2, 0)
      expect(settleBet('btts_yes_ft', fixture)).toBe('lost')
    })

    test('btts_yes_ft: lost when only away scores', () => {
      const fixture = createFixture('FT', 0, 1)
      expect(settleBet('btts_yes_ft', fixture)).toBe('lost')
    })

    test('btts_yes_ft: lost when 0-0', () => {
      const fixture = createFixture('FT', 0, 0)
      expect(settleBet('btts_yes_ft', fixture)).toBe('lost')
    })

    test('btts_no_ft: won when only home scores', () => {
      const fixture = createFixture('FT', 2, 0)
      expect(settleBet('btts_no_ft', fixture)).toBe('won')
    })

    test('btts_no_ft: won when 0-0', () => {
      const fixture = createFixture('FT', 0, 0)
      expect(settleBet('btts_no_ft', fixture)).toBe('won')
    })

    test('btts_no_ft: lost when both teams score', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('btts_no_ft', fixture)).toBe('lost')
    })
  })

  describe('Result 1X2', () => {
    test('home_win_ft: won when home wins', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('home_win_ft', fixture)).toBe('won')
    })

    test('home_win_ft: lost when draw', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('home_win_ft', fixture)).toBe('lost')
    })

    test('home_win_ft: lost when away wins', () => {
      const fixture = createFixture('FT', 0, 1)
      expect(settleBet('home_win_ft', fixture)).toBe('lost')
    })

    test('draw_ft: won when draw', () => {
      const fixture = createFixture('FT', 2, 2)
      expect(settleBet('draw_ft', fixture)).toBe('won')
    })

    test('draw_ft: lost when home wins', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('draw_ft', fixture)).toBe('lost')
    })

    test('away_win_ft: won when away wins', () => {
      const fixture = createFixture('FT', 1, 3)
      expect(settleBet('away_win_ft', fixture)).toBe('won')
    })

    test('away_win_ft: lost when home wins', () => {
      const fixture = createFixture('FT', 2, 0)
      expect(settleBet('away_win_ft', fixture)).toBe('lost')
    })
  })

  describe('Double Chance', () => {
    test('dc_1x_ft: won when home wins', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('dc_1x_ft', fixture)).toBe('won')
    })

    test('dc_1x_ft: won when draw', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('dc_1x_ft', fixture)).toBe('won')
    })

    test('dc_1x_ft: lost when away wins', () => {
      const fixture = createFixture('FT', 0, 1)
      expect(settleBet('dc_1x_ft', fixture)).toBe('lost')
    })

    test('dc_x2_ft: won when away wins', () => {
      const fixture = createFixture('FT', 1, 2)
      expect(settleBet('dc_x2_ft', fixture)).toBe('won')
    })

    test('dc_x2_ft: won when draw', () => {
      const fixture = createFixture('FT', 0, 0)
      expect(settleBet('dc_x2_ft', fixture)).toBe('won')
    })

    test('dc_x2_ft: lost when home wins', () => {
      const fixture = createFixture('FT', 3, 1)
      expect(settleBet('dc_x2_ft', fixture)).toBe('lost')
    })

    test('dc_12_ft: won when home wins', () => {
      const fixture = createFixture('FT', 2, 0)
      expect(settleBet('dc_12_ft', fixture)).toBe('won')
    })

    test('dc_12_ft: won when away wins', () => {
      const fixture = createFixture('FT', 0, 1)
      expect(settleBet('dc_12_ft', fixture)).toBe('won')
    })

    test('dc_12_ft: lost when draw', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('dc_12_ft', fixture)).toBe('lost')
    })
  })

  describe('Half Time Goals', () => {
    test('over_0_5_ht: won with 1 HT goal', () => {
      const fixture = createFixture('FT', 2, 1, 1, 0)
      expect(settleBet('over_0_5_ht', fixture)).toBe('won')
    })

    test('over_0_5_ht: lost with 0 HT goals', () => {
      const fixture = createFixture('FT', 2, 1, 0, 0)
      expect(settleBet('over_0_5_ht', fixture)).toBe('lost')
    })

    test('over_1_5_ht: won with 2 HT goals', () => {
      const fixture = createFixture('FT', 3, 2, 1, 1)
      expect(settleBet('over_1_5_ht', fixture)).toBe('won')
    })

    test('over_1_5_ht: lost with 1 HT goal', () => {
      const fixture = createFixture('FT', 2, 1, 1, 0)
      expect(settleBet('over_1_5_ht', fixture)).toBe('lost')
    })

    test('HT market: void when no HT data', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('over_0_5_ht', fixture)).toBe('void')
    })
  })

  describe('Corners', () => {
    test('corners_over_8_5_ft: won with 9 corners', () => {
      const fixture = createFixture('FT', 1, 1, null, null, 9)
      expect(settleBet('corners_over_8_5_ft', fixture)).toBe('won')
    })

    test('corners_over_8_5_ft: lost with 8 corners', () => {
      const fixture = createFixture('FT', 1, 1, null, null, 8)
      expect(settleBet('corners_over_8_5_ft', fixture)).toBe('lost')
    })

    test('corners_over_9_5_ft: won with 10 corners', () => {
      const fixture = createFixture('FT', 1, 1, null, null, 10)
      expect(settleBet('corners_over_9_5_ft', fixture)).toBe('won')
    })

    test('corners_over_9_5_ft: lost with 9 corners', () => {
      const fixture = createFixture('FT', 1, 1, null, null, 9)
      expect(settleBet('corners_over_9_5_ft', fixture)).toBe('lost')
    })

    test('corners_over_9_5_ft: won with 11 corners', () => {
      const fixture = createFixture('FT', 1, 1, null, null, 11)
      expect(settleBet('corners_over_9_5_ft', fixture)).toBe('won')
    })

    test('corners market: void when no corners data', () => {
      const fixture = createFixture('FT', 1, 1)
      expect(settleBet('corners_over_8_5_ft', fixture)).toBe('void')
    })
  })

  describe('Edge Cases', () => {
    test('unknown market returns void', () => {
      const fixture = createFixture('FT', 2, 1)
      expect(settleBet('unknown_market', fixture)).toBe('void')
    })

    test('null goals returns void', () => {
      const fixture = createFixture('FT', null, null)
      expect(settleBet('over_2_5_ft', fixture)).toBe('void')
    })

    test('high scoring game', () => {
      const fixture = createFixture('FT', 5, 4)
      expect(settleBet('over_3_5_ft', fixture)).toBe('won')
      expect(settleBet('under_3_5_ft', fixture)).toBe('lost')
      expect(settleBet('btts_yes_ft', fixture)).toBe('won')
    })
  })
})
