#!/usr/bin/env python3

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import telegram_changes as tc  # noqa: E402


def make_offer(slug: str = "bbva", **extra: object) -> dict:
    offer = {
        "slug": slug,
        "name": slug.upper(),
        "status": "active",
        "bonus_cliente": "10€",
        "bonus_cliente_fixed": True,
        "bonus_note": "Promo valida fino al 20 luglio 2026",
        "effective_gain": "10€ pieni",
        "effective_gain_note": "Un acquisto.",
        "deposit_required": "1 acquisto",
        "requirements": ["Nuovo cliente"],
        "referral_code": "SEGRETO123",
        "referral_url": "https://esempio.test/invito/SEGRETO123",
        "guide_url": f"bonus-{slug}.html",
        "last_verified_at": "2026-03-23",
    }
    offer.update(extra)
    return offer


class DetectChangesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.offers = [make_offer("bbva"), make_offer("revolut")]
        self.state = tc.build_state(self.offers)

    def test_no_change(self) -> None:
        self.assertEqual(tc.detect_changes(self.offers, self.state), [])

    def test_irrelevant_fields_are_ignored(self) -> None:
        changed = copy.deepcopy(self.offers)
        changed[0]["last_verified_at"] = "2026-09-01"
        changed[0]["referral_url"] = "https://altro.test/x"
        self.assertEqual(tc.detect_changes(changed, self.state), [])

    def test_changed_expiry(self) -> None:
        changed = copy.deepcopy(self.offers)
        changed[0]["bonus_note"] = "Promo valida fino al 31 dicembre 2026"
        result = tc.detect_changes(changed, self.state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["offer"]["slug"], "bbva")
        self.assertIn("scadenza", result[0]["note"])

    def test_changed_amount_and_requirements(self) -> None:
        changed = copy.deepcopy(self.offers)
        changed[1]["bonus_cliente"] = "20€"
        changed[1]["requirements"] = ["Altro"]
        note = tc.detect_changes(changed, self.state)[0]["note"]
        self.assertIn("importo del bonus", note)
        self.assertIn("requisiti", note)

    def test_new_offer(self) -> None:
        offers = self.offers + [make_offer("nuova")]
        result = tc.detect_changes(offers, self.state)
        self.assertEqual([c["offer"]["slug"] for c in result], ["nuova"])
        self.assertTrue(result[0]["note"].startswith("Novità"))

    def test_state_has_no_plain_secrets(self) -> None:
        self.assertNotIn("SEGRETO123", str(self.state))


class WeeklyTest(unittest.TestCase):
    def test_summary_one_line_per_bank_without_invite(self) -> None:
        offers = [make_offer("bbva"), make_offer("revolut", bonus_note="Variabile")]
        text = tc.build_weekly_text(offers, "https://sito.test")
        self.assertEqual(text.count("• "), 2)
        self.assertIn("https://sito.test/bonus-bbva.html", text)
        self.assertIn("valida fino al 20 luglio 2026", text)
        self.assertIn("scadenza non indicata", text)
        self.assertNotIn("SEGRETO123", text)
        self.assertNotIn("esempio.test", text)

    def test_weekly_only_on_monday_or_forced(self) -> None:
        import datetime as dt

        monday = dt.date(2026, 9, 28)
        self.assertTrue(tc.should_send_weekly("auto", monday))
        self.assertFalse(tc.should_send_weekly("auto", dt.date(2026, 9, 29)))
        self.assertTrue(tc.should_send_weekly("force-weekly", dt.date(2026, 9, 29)))


class MaskTest(unittest.TestCase):
    def test_mask_hides_code_and_url(self) -> None:
        offers = [make_offer()]
        text = "Codice SEGRETO123 su https://esempio.test/invito/SEGRETO123"
        masked = tc.mask(text, offers)
        self.assertNotIn("SEGRETO123", masked)
        self.assertEqual(masked, "Codice *** su ***")


if __name__ == "__main__":
    unittest.main()
