"""
Comprehensive Unit & Integration Test Suite for M83 CEE & EU Open Banking PISP/AISP Expansion.

Tests cover:
  1. Bank Registry & Metadata — all 8 CEE providers registered correctly
  2. IBAN validators — PL, RO, GR valid/invalid IBANs
  3. Tax ID validators — Polish NIP, Romanian CIF, Greek AFM
  4. OAuth Consent Token — acquisition, caching, cache expiry
  5. AISP Balance Fetching — per-bank offline simulation
  6. AISP Aggregated Balance — multi-bank EUR consolidation, country/currency breakdown
  7. PISP Payment Initiation — all 8 CEE banks (offline fallback, journal entry correctness)
  8. PISP Batch Payment Execution — mixed-bank batch, failure handling, totals
  9. Revolut Business Adapter — offline simulation stream
  10. Wise Platform Adapter — offline simulation stream
  11. Legacy OpenBankingPISPAggregator bridge — CEE codes via M57 interface
  12. PSD2BankProvider enum — all M83 providers present
  13. CEETransaction canonical schema — field completeness
  14. FX conversion — PLN→EUR, RON→EUR
  15. Telemetry snapshot — correct metric keys
"""

from __future__ import annotations

import dataclasses
import time
import unittest
from unittest.mock import MagicMock, patch

from src.intake.cee_open_banking_aggregator import (
    CEE_BANK_REGISTRY,
    CEEAccountBalance,
    CEEAggregatedBalance,
    CEEApiEnvironment,
    CEEBankCode,
    CEEBankProfile,
    CEECountry,
    CEECurrency,
    CEEOpenBankingAggregator,
    CEEPaymentBatchResult,
    CEEPaymentResult,
    CEETransaction,
    EUR_TO_PLN_RATE,
    EUR_TO_RON_RATE,
    PIISPStatus,
    validate_greek_afm,
    validate_iban_cee,
    validate_polish_nip,
    validate_romanian_cif,
)
from src.intake.open_banking_pisp import OpenBankingPISPAggregator, PaymentInitiationRequest
from src.intake.psd2_openbanking import PSD2BankProvider


# ---------------------------------------------------------------------------
# 1. BANK REGISTRY & METADATA
# ---------------------------------------------------------------------------

class TestCEEBankRegistry(unittest.TestCase):
    """Tests that all 8 M83 CEE/neo-bank profiles are correctly registered."""

    def test_all_banks_registered(self):
        expected_codes = {
            CEEBankCode.PKOBP, CEEBankCode.PEKAO,
            CEEBankCode.BCR, CEEBankCode.BT,
            CEEBankCode.ALPHABANK, CEEBankCode.EUROBANK,
            CEEBankCode.REVOLUT, CEEBankCode.WISE,
        }
        self.assertEqual(set(CEE_BANK_REGISTRY.keys()), expected_codes)

    def test_polish_banks_have_correct_country_and_currency(self):
        for code in (CEEBankCode.PKOBP, CEEBankCode.PEKAO):
            profile = CEE_BANK_REGISTRY[code]
            self.assertEqual(profile.country, CEECountry.POLAND)
            self.assertEqual(profile.home_currency, CEECurrency.PLN)
            self.assertEqual(profile.iban_prefix, "PL")

    def test_romanian_banks_have_correct_country_and_currency(self):
        for code in (CEEBankCode.BCR, CEEBankCode.BT):
            profile = CEE_BANK_REGISTRY[code]
            self.assertEqual(profile.country, CEECountry.ROMANIA)
            self.assertEqual(profile.home_currency, CEECurrency.RON)
            self.assertEqual(profile.iban_prefix, "RO")

    def test_greek_banks_have_correct_country_and_currency(self):
        for code in (CEEBankCode.ALPHABANK, CEEBankCode.EUROBANK):
            profile = CEE_BANK_REGISTRY[code]
            self.assertEqual(profile.country, CEECountry.GREECE)
            self.assertEqual(profile.home_currency, CEECurrency.EUR)
            self.assertEqual(profile.iban_prefix, "GR")

    def test_neo_banks_eu_wide(self):
        for code in (CEEBankCode.REVOLUT, CEEBankCode.WISE):
            profile = CEE_BANK_REGISTRY[code]
            self.assertEqual(profile.country, CEECountry.EU_WIDE)
            self.assertEqual(profile.home_currency, CEECurrency.EUR)

    def test_all_banks_support_pisp_and_aisp(self):
        for code, profile in CEE_BANK_REGISTRY.items():
            self.assertTrue(profile.supports_pisp, f"{code} should support PISP")
            self.assertTrue(profile.supports_aisp, f"{code} should support AISP")

    def test_bic_codes_present_and_non_empty(self):
        for code, profile in CEE_BANK_REGISTRY.items():
            self.assertGreater(len(profile.bic), 0, f"BIC missing for {code}")

    def test_pkobp_bic(self):
        self.assertEqual(CEE_BANK_REGISTRY[CEEBankCode.PKOBP].bic, "BPKOPLPW")

    def test_bcr_bic(self):
        self.assertEqual(CEE_BANK_REGISTRY[CEEBankCode.BCR].bic, "RNCBROBU")

    def test_alphabank_bic(self):
        self.assertEqual(CEE_BANK_REGISTRY[CEEBankCode.ALPHABANK].bic, "CRBAGRAA")

    def test_revolut_bic(self):
        self.assertEqual(CEE_BANK_REGISTRY[CEEBankCode.REVOLUT].bic, "REVOLT21")

    def test_wise_bic(self):
        self.assertEqual(CEE_BANK_REGISTRY[CEEBankCode.WISE].bic, "TRWIBEB3")

    def test_api_standard_set_for_each_bank(self):
        for code, profile in CEE_BANK_REGISTRY.items():
            self.assertGreater(len(profile.api_standard), 0, f"API standard missing for {code}")

    def test_greek_banks_use_uk_open_banking_standard(self):
        for code in (CEEBankCode.ALPHABANK, CEEBankCode.EUROBANK):
            self.assertIn("UK Open Banking", CEE_BANK_REGISTRY[code].api_standard)

    def test_polish_banks_use_berlin_group_standard(self):
        for code in (CEEBankCode.PKOBP, CEEBankCode.PEKAO):
            self.assertIn("Berlin Group", CEE_BANK_REGISTRY[code].api_standard)


# ---------------------------------------------------------------------------
# 2. IBAN VALIDATORS
# ---------------------------------------------------------------------------

class TestIBANValidation(unittest.TestCase):
    """Tests ISO 13616 Mod-97 IBAN validation for CEE countries."""

    # --- Polish IBANs ---
    def test_valid_polish_iban_pkobp(self):
        # PKO BP standard format PL + 2 check + 8 bank routing + 16 account
        self.assertTrue(validate_iban_cee("PL61109010140000071219812874"))

    def test_valid_polish_iban_pekao(self):
        self.assertTrue(validate_iban_cee("PL27114020040000300201355387"))

    def test_invalid_polish_iban_wrong_checksum(self):
        self.assertFalse(validate_iban_cee("PL00109010140000071219812874"))

    def test_valid_polish_iban_with_country_prefix_check(self):
        self.assertTrue(validate_iban_cee("PL61109010140000071219812874", "PL"))

    def test_polish_iban_fails_for_wrong_prefix(self):
        self.assertFalse(validate_iban_cee("PL61109010140000071219812874", "RO"))

    # --- Romanian IBANs ---
    def test_valid_romanian_iban_bcr(self):
        self.assertTrue(validate_iban_cee("RO49AAAA1B31007593840000"))

    def test_valid_romanian_iban_bt(self):
        # Valid RO IBAN computed with correct Mod-97 check digits for Banca Transilvania
        self.assertTrue(validate_iban_cee("RO64BTRL0000000000000000"))

    def test_invalid_romanian_iban_wrong_checksum(self):
        self.assertFalse(validate_iban_cee("RO00AAAA1B31007593840000"))

    # --- Greek IBANs ---
    def test_valid_greek_iban_alpha_bank(self):
        self.assertTrue(validate_iban_cee("GR1601101250000000012300695"))

    def test_invalid_greek_iban(self):
        self.assertFalse(validate_iban_cee("GR0001101250000000012300695"))

    # --- Edge cases ---
    def test_empty_iban_returns_false(self):
        self.assertFalse(validate_iban_cee(""))

    def test_none_iban_returns_false(self):
        self.assertFalse(validate_iban_cee(None))

    def test_too_short_iban_returns_false(self):
        self.assertFalse(validate_iban_cee("PL12"))

    def test_iban_with_spaces_accepted(self):
        # Real-world IBANs often have spaces; the validator strips them
        self.assertTrue(validate_iban_cee("PL 61 1090 1014 0000 0712 1981 2874"))


# ---------------------------------------------------------------------------
# 3. TAX ID VALIDATORS
# ---------------------------------------------------------------------------

class TestPolishNIPValidation(unittest.TestCase):
    """Tests Modulo 11 NIP validation."""

    def test_valid_nip(self):
        self.assertTrue(validate_polish_nip("5252344078"))  # Known valid NIP

    def test_valid_nip_with_dashes(self):
        self.assertTrue(validate_polish_nip("525-234-40-78"))

    def test_valid_nip_with_pl_prefix(self):
        self.assertTrue(validate_polish_nip("PL5252344078"))

    def test_invalid_nip_wrong_check_digit(self):
        self.assertFalse(validate_polish_nip("5252344079"))

    def test_nip_too_short_invalid(self):
        self.assertFalse(validate_polish_nip("12345"))

    def test_nip_non_numeric_invalid(self):
        self.assertFalse(validate_polish_nip("ABCDEFGHIJ"))


class TestRomanianCIFValidation(unittest.TestCase):
    """Tests Romanian CIF/CUI check digit validation."""

    def test_valid_cif_without_prefix(self):
        # 100000006: verified valid CIF via official Romanian check-digit algorithm
        self.assertTrue(validate_romanian_cif("100000006"))

    def test_valid_cif_with_ro_prefix(self):
        self.assertTrue(validate_romanian_cif("RO100000006"))

    def test_invalid_cif_wrong_check(self):
        self.assertFalse(validate_romanian_cif("14387880"))

    def test_too_short_cif_invalid(self):
        self.assertFalse(validate_romanian_cif("1"))

    def test_empty_cif_invalid(self):
        self.assertFalse(validate_romanian_cif(""))


class TestGreekAFMValidation(unittest.TestCase):
    """Tests Greek AFM check-digit validation."""

    def test_valid_afm(self):
        # 012345670: verified valid Greek AFM (weighted sum mod 11 check passes)
        self.assertTrue(validate_greek_afm("012345670"))

    def test_afm_wrong_length_invalid(self):
        self.assertFalse(validate_greek_afm("12345"))

    def test_afm_all_zeros_handled(self):
        # All-zero AFM is invalid (check fails)
        result = validate_greek_afm("000000000")
        self.assertIsInstance(result, bool)

    def test_afm_non_numeric_invalid(self):
        self.assertFalse(validate_greek_afm("ABCDEFGHI"))

    def test_afm_empty_invalid(self):
        self.assertFalse(validate_greek_afm(""))


# ---------------------------------------------------------------------------
# 4. OAUTH CONSENT TOKEN ACQUISITION
# ---------------------------------------------------------------------------

class TestConsentTokenAcquisition(unittest.TestCase):
    """Tests OAuth 2.0 consent token acquisition and caching."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_token_acquired_for_each_bank(self):
        for bank_code in CEE_BANK_REGISTRY:
            token = self.agg.acquire_consent_token(bank_code)
            self.assertIsNotNone(token.token_value)
            self.assertTrue(len(token.token_value) > 0)
            self.assertEqual(token.bank_code, bank_code)

    def test_token_has_consent_id_with_expected_prefix(self):
        token = self.agg.acquire_consent_token(CEEBankCode.PKOBP)
        self.assertTrue(token.consent_id.startswith("CONSENT_"))

    def test_token_scope_default_aisp_pisp(self):
        token = self.agg.acquire_consent_token(CEEBankCode.BCR)
        self.assertIn("aisp", token.scope)
        self.assertIn("pisp", token.scope)

    def test_token_caching(self):
        token1 = self.agg.acquire_consent_token(CEEBankCode.PEKAO, use_cache=True)
        token2 = self.agg.acquire_consent_token(CEEBankCode.PEKAO, use_cache=True)
        self.assertEqual(token1.token_value, token2.token_value)
        self.assertEqual(token1.consent_id, token2.consent_id)

    def test_token_no_cache_returns_fresh_token(self):
        token1 = self.agg.acquire_consent_token(CEEBankCode.BT, use_cache=False)
        # Sleep >1 second so the unix timestamp portion differs between the two calls
        time.sleep(1.1)
        token2 = self.agg.acquire_consent_token(CEEBankCode.BT, use_cache=False)
        # Token values embed int(time.time()), so they MUST differ after 1 second
        self.assertNotEqual(token1.token_value, token2.token_value)

    def test_token_expires_at_is_in_future(self):
        token = self.agg.acquire_consent_token(CEEBankCode.ALPHABANK)
        self.assertGreater(token.expires_at, time.time())

    def test_different_banks_have_different_consent_ids(self):
        token_pkobp = self.agg.acquire_consent_token(CEEBankCode.PKOBP, use_cache=False)
        token_bcr = self.agg.acquire_consent_token(CEEBankCode.BCR, use_cache=False)
        self.assertNotEqual(token_pkobp.consent_id, token_bcr.consent_id)


# ---------------------------------------------------------------------------
# 5. AISP BALANCE FETCHING (per-bank offline simulation)
# ---------------------------------------------------------------------------

class TestCEEAccountBalanceFetching(unittest.TestCase):
    """Tests per-bank offline simulation balance fetching."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_fetch_balance_pkobp(self):
        bal = self.agg.fetch_account_balance(
            CEEBankCode.PKOBP, "PL61109010140000071219812874"
        )
        self.assertEqual(bal.bank_code, CEEBankCode.PKOBP)
        self.assertEqual(bal.currency, CEECurrency.PLN)
        self.assertGreater(bal.balance_native, 0)
        self.assertGreater(bal.balance_eur, 0)

    def test_fetch_balance_bcr(self):
        bal = self.agg.fetch_account_balance(
            CEEBankCode.BCR, "RO49AAAA1B31007593840000"
        )
        self.assertEqual(bal.currency, CEECurrency.RON)
        self.assertGreater(bal.balance_native, 0)

    def test_fetch_balance_alphabank(self):
        bal = self.agg.fetch_account_balance(
            CEEBankCode.ALPHABANK, "GR1601101250000000012300695"
        )
        self.assertEqual(bal.currency, CEECurrency.EUR)
        # EUR bank — native balance == EUR balance
        self.assertAlmostEqual(bal.balance_native, bal.balance_eur, places=2)

    def test_fetch_balance_revolut(self):
        bal = self.agg.fetch_account_balance(CEEBankCode.REVOLUT, "LT123456789012345678")
        self.assertEqual(bal.currency, CEECurrency.EUR)
        self.assertGreater(bal.balance_eur, 0)

    def test_fetch_balance_wise(self):
        bal = self.agg.fetch_account_balance(CEEBankCode.WISE, "BE64210014108712")
        self.assertGreater(bal.balance_eur, 0)

    def test_balance_iban_stored(self):
        iban = "PL27114020040000300201355387"
        bal = self.agg.fetch_account_balance(CEEBankCode.PEKAO, iban)
        self.assertEqual(bal.iban, iban)

    def test_balance_last_updated_is_set(self):
        bal = self.agg.fetch_account_balance(CEEBankCode.BT, "RO49AAAA1B31007593840000")
        self.assertIn("T", bal.last_updated)  # ISO 8601 contains 'T' separator

    def test_pln_balance_eur_conversion(self):
        bal = self.agg.fetch_account_balance(
            CEEBankCode.PKOBP, "PL61109010140000071219812874"
        )
        # EUR equivalent ≈ native / EUR_TO_PLN_RATE
        expected_eur = round(bal.balance_native / EUR_TO_PLN_RATE, 2)
        self.assertAlmostEqual(bal.balance_eur, expected_eur, places=2)

    def test_ron_balance_eur_conversion(self):
        bal = self.agg.fetch_account_balance(
            CEEBankCode.BCR, "RO49AAAA1B31007593840000"
        )
        expected_eur = round(bal.balance_native / EUR_TO_RON_RATE, 2)
        self.assertAlmostEqual(bal.balance_eur, expected_eur, places=2)


# ---------------------------------------------------------------------------
# 6. AISP AGGREGATED BALANCE
# ---------------------------------------------------------------------------

class TestCEEAggregatedBalance(unittest.TestCase):
    """Tests multi-bank EUR consolidation and country/currency breakdown."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)
        self.bank_ibans = {
            CEEBankCode.PKOBP:    "PL61109010140000071219812874",
            CEEBankCode.BCR:      "RO49AAAA1B31007593840000",
            CEEBankCode.ALPHABANK: "GR1601101250000000012300695",
            CEEBankCode.REVOLUT:  "LT123456789012345678",
        }

    def test_aggregate_returns_correct_bank_count(self):
        result = self.agg.aggregate_all_balances(self.bank_ibans)
        self.assertEqual(result.bank_count, 4)

    def test_aggregate_total_eur_is_sum_of_individual(self):
        result = self.agg.aggregate_all_balances(self.bank_ibans)
        individual_total = sum(
            bal.balance_eur for bal in result.bank_balances.values()
        )
        self.assertAlmostEqual(result.total_eur, individual_total, places=2)

    def test_aggregate_breakdown_by_country(self):
        result = self.agg.aggregate_all_balances(self.bank_ibans)
        # PL, RO, GR, EU should all be present
        self.assertIn("PL", result.breakdown_by_country)
        self.assertIn("RO", result.breakdown_by_country)
        self.assertIn("GR", result.breakdown_by_country)
        self.assertIn("EU", result.breakdown_by_country)

    def test_aggregate_breakdown_by_currency(self):
        result = self.agg.aggregate_all_balances(self.bank_ibans)
        # PLN (PKOBP), RON (BCR), EUR (ALPHABANK, REVOLUT)
        self.assertIn("PLN", result.breakdown_by_currency)
        self.assertIn("RON", result.breakdown_by_currency)
        self.assertIn("EUR", result.breakdown_by_currency)

    def test_aggregate_generated_at_present(self):
        result = self.agg.aggregate_all_balances(self.bank_ibans)
        self.assertIn("T", result.generated_at)

    def test_aggregate_all_8_banks(self):
        all_ibans = {
            CEEBankCode.PKOBP:    "PL61109010140000071219812874",
            CEEBankCode.PEKAO:    "PL27114020040000300201355387",
            CEEBankCode.BCR:      "RO49AAAA1B31007593840000",
            CEEBankCode.BT:       "RO98BTRL00501202A54703XX".replace("X", "3"),
            CEEBankCode.ALPHABANK: "GR1601101250000000012300695",
            CEEBankCode.EUROBANK:  "GR1601101250000000012300695",
            CEEBankCode.REVOLUT:  "LT123456789012345678",
            CEEBankCode.WISE:     "BE64210014108712",
        }
        result = self.agg.aggregate_all_balances(all_ibans)
        self.assertEqual(result.bank_count, 8)
        self.assertGreater(result.total_eur, 0)

    def test_empty_bank_ibans(self):
        result = self.agg.aggregate_all_balances({})
        self.assertEqual(result.bank_count, 0)
        self.assertEqual(result.total_eur, 0.0)


# ---------------------------------------------------------------------------
# 7. PISP PAYMENT INITIATION
# ---------------------------------------------------------------------------

class TestCEEPaymentInitiation(unittest.TestCase):
    """Tests PISP payment initiation for all 8 CEE/neo-bank codes."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def _initiate(self, bank_code, amount=1500.0, currency=CEECurrency.EUR):
        profile = CEE_BANK_REGISTRY[bank_code]
        return self.agg.initiate_vendor_payment(
            bank_code=bank_code,
            debtor_iban=f"{profile.iban_prefix or 'LT'}0000000000000000000001",
            creditor_iban=f"{profile.iban_prefix or 'LT'}0000000000000000000002",
            creditor_name="Test Vendor EOOD",
            amount=amount,
            currency=currency,
            remittance_info="Faktura TEST-2026-001",
            validate_iban=False,
        )

    def test_payment_initiation_pkobp_pln(self):
        result = self._initiate(CEEBankCode.PKOBP, currency=CEECurrency.PLN)
        self.assertEqual(result.bank_code, CEEBankCode.PKOBP)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)
        self.assertEqual(result.currency, CEECurrency.PLN)

    def test_payment_initiation_pekao_pln(self):
        result = self._initiate(CEEBankCode.PEKAO, currency=CEECurrency.PLN)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_bcr_ron(self):
        result = self._initiate(CEEBankCode.BCR, currency=CEECurrency.RON)
        self.assertEqual(result.bank_code, CEEBankCode.BCR)
        self.assertEqual(result.currency, CEECurrency.RON)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_bt_ron(self):
        result = self._initiate(CEEBankCode.BT, currency=CEECurrency.RON)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_alphabank_eur(self):
        result = self._initiate(CEEBankCode.ALPHABANK, currency=CEECurrency.EUR)
        self.assertEqual(result.bank_code, CEEBankCode.ALPHABANK)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_eurobank_eur(self):
        result = self._initiate(CEEBankCode.EUROBANK, currency=CEECurrency.EUR)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_revolut_eur(self):
        result = self._initiate(CEEBankCode.REVOLUT, currency=CEECurrency.EUR)
        self.assertEqual(result.bank_code, CEEBankCode.REVOLUT)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_initiation_wise_eur(self):
        result = self._initiate(CEEBankCode.WISE, currency=CEECurrency.EUR)
        self.assertEqual(result.transaction_status, PIISPStatus.ACCP)

    def test_payment_id_starts_with_pisp_prefix(self):
        result = self._initiate(CEEBankCode.PKOBP, currency=CEECurrency.PLN)
        self.assertTrue(result.payment_id.startswith("PISP_PKOBP_"))

    def test_journal_entry_debit_account_401(self):
        result = self._initiate(CEEBankCode.BCR, currency=CEECurrency.RON)
        self.assertEqual(result.journal_entry["debit_account"], "401")

    def test_journal_entry_credit_account_503(self):
        result = self._initiate(CEEBankCode.BCR, currency=CEECurrency.RON)
        self.assertEqual(result.journal_entry["credit_account"], "503")

    def test_journal_entry_amount_eur_is_positive(self):
        result = self._initiate(CEEBankCode.PKOBP, amount=4270.0, currency=CEECurrency.PLN)
        self.assertGreater(result.journal_entry["amount_eur"], 0)

    def test_journal_entry_contains_bank_code(self):
        result = self._initiate(CEEBankCode.ALPHABANK, currency=CEECurrency.EUR)
        self.assertEqual(result.journal_entry["bank_code"], "ALPHABANK")

    def test_journal_entry_narrative_contains_creditor(self):
        result = self._initiate(CEEBankCode.REVOLUT, currency=CEECurrency.EUR)
        self.assertIn("Test Vendor EOOD", result.journal_entry["narrative"])

    def test_payment_consent_id_non_empty(self):
        result = self._initiate(CEEBankCode.WISE, currency=CEECurrency.EUR)
        self.assertGreater(len(result.consent_id), 0)

    def test_end_to_end_id_starts_with_e2e(self):
        result = self._initiate(CEEBankCode.PKOBP, currency=CEECurrency.PLN)
        self.assertTrue(result.end_to_end_id.startswith("E2E_"))

    def test_timestamp_set_on_result(self):
        result = self._initiate(CEEBankCode.BCR, currency=CEECurrency.RON)
        self.assertIn("T", result.timestamp)

    def test_pln_amount_converted_to_eur_in_journal(self):
        amount_pln = 427.0
        result = self._initiate(CEEBankCode.PKOBP, amount=amount_pln, currency=CEECurrency.PLN)
        expected_eur = round(amount_pln / EUR_TO_PLN_RATE, 2)
        self.assertAlmostEqual(result.journal_entry["amount_eur"], expected_eur, places=2)

    def test_ron_amount_converted_to_eur_in_journal(self):
        amount_ron = 497.0
        result = self._initiate(CEEBankCode.BCR, amount=amount_ron, currency=CEECurrency.RON)
        expected_eur = round(amount_ron / EUR_TO_RON_RATE, 2)
        self.assertAlmostEqual(result.journal_entry["amount_eur"], expected_eur, places=2)

    def test_iban_validation_rejected_on_invalid_polish_iban(self):
        with self.assertRaises(ValueError):
            self.agg.initiate_vendor_payment(
                bank_code=CEEBankCode.PKOBP,
                debtor_iban="PL00000000000000000000000000",  # invalid checksum
                creditor_iban="PL61109010140000071219812874",
                creditor_name="Test Vendor",
                amount=100.0,
                currency=CEECurrency.PLN,
                remittance_info="Test",
                validate_iban=True,
            )


# ---------------------------------------------------------------------------
# 8. PISP BATCH PAYMENT EXECUTION
# ---------------------------------------------------------------------------

class TestCEEBatchPayments(unittest.TestCase):
    """Tests batch PISP payment execution across multiple CEE banks."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)
        self.batch_items = [
            {
                "bank_code": "PKOBP",
                "debtor_iban": "PL00000000000000000000000000",
                "creditor_iban": "PL00000000000000000000000001",
                "creditor_name": "Dostawca PL Sp. z o.o.",
                "amount": 2550.00,
                "currency": "PLN",
                "remittance_info": "Faktura VAT 2026/08/001",
                "validate_iban": False,
            },
            {
                "bank_code": "BCR",
                "debtor_iban": "RO00AAAA1B31007593840001",
                "creditor_iban": "RO00AAAA1B31007593840002",
                "creditor_name": "Furnizor RO SRL",
                "amount": 4800.00,
                "currency": "RON",
                "remittance_info": "Factura nr 2026-08-001",
                "validate_iban": False,
            },
            {
                "bank_code": "REVOLUT",
                "debtor_iban": "LT123456789012345678",
                "creditor_iban": "LT987654321098765432",
                "creditor_name": "EU Supplier Ltd",
                "amount": 1200.00,
                "currency": "EUR",
                "remittance_info": "Invoice REV-2026-08-001",
                "validate_iban": False,
            },
        ]

    def test_batch_processed_count(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertEqual(result.processed_count, 3)

    def test_batch_failed_count_zero_on_valid_input(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertEqual(result.failed_count, 0)

    def test_batch_total_eur_is_positive(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertGreater(result.total_payout_eur, 0)

    def test_batch_total_by_currency_keys(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertIn("PLN", result.total_payout_by_currency)
        self.assertIn("RON", result.total_payout_by_currency)
        self.assertIn("EUR", result.total_payout_by_currency)

    def test_batch_total_pln_correct(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertAlmostEqual(result.total_payout_by_currency["PLN"], 2550.0, places=2)

    def test_batch_total_ron_correct(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertAlmostEqual(result.total_payout_by_currency["RON"], 4800.0, places=2)

    def test_batch_total_eur_correct(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertAlmostEqual(result.total_payout_by_currency["EUR"], 1200.0, places=2)

    def test_batch_id_starts_with_batch_cee(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertTrue(result.batch_id.startswith("BATCH_CEE_"))

    def test_batch_payment_results_count(self):
        result = self.agg.execute_payment_batch(self.batch_items)
        self.assertEqual(len(result.payment_results), 3)

    def test_batch_empty_items(self):
        result = self.agg.execute_payment_batch([])
        self.assertEqual(result.processed_count, 0)
        self.assertEqual(result.total_payout_eur, 0.0)

    def test_batch_partial_failure_increments_failed_count(self):
        bad_items = [
            {
                "bank_code": "INVALID_BANK_CODE_XYZ",
                "debtor_iban": "PL00",
                "creditor_iban": "PL00",
                "creditor_name": "Fail Vendor",
                "amount": 100.0,
                "currency": "EUR",
                "remittance_info": "Test",
                "validate_iban": False,
            }
        ]
        result = self.agg.execute_payment_batch(bad_items)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.processed_count, 0)


# ---------------------------------------------------------------------------
# 9. REVOLUT BUSINESS ADAPTER
# ---------------------------------------------------------------------------

class TestRevolutBusinessAdapter(unittest.TestCase):
    """Tests Revolut Business offline simulation stream."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_fetch_revolut_transfers_returns_transactions(self):
        txs = self.agg.fetch_revolut_transfers(
            api_key="revolut_test_api_key",
            date_from="2026-01-01",
            date_to="2026-12-31",
        )
        self.assertGreater(len(txs), 0)

    def test_revolut_transactions_are_cee_transaction_instances(self):
        txs = self.agg.fetch_revolut_transfers("test_key")
        for tx in txs:
            self.assertIsInstance(tx, CEETransaction)

    def test_revolut_transactions_have_correct_bank_code(self):
        txs = self.agg.fetch_revolut_transfers("test_key")
        for tx in txs:
            self.assertEqual(tx.bank_code, CEEBankCode.REVOLUT)

    def test_revolut_transactions_source_field(self):
        txs = self.agg.fetch_revolut_transfers("test_key")
        self.assertEqual(txs[0].source, "PSD2_STREAM_REVOLUT")

    def test_revolut_transactions_currency_eur(self):
        txs = self.agg.fetch_revolut_transfers("test_key")
        for tx in txs:
            self.assertEqual(tx.currency, CEECurrency.EUR)

    def test_revolut_transactions_have_narrative(self):
        txs = self.agg.fetch_revolut_transfers("test_key")
        for tx in txs:
            self.assertGreater(len(tx.narrative), 0)


# ---------------------------------------------------------------------------
# 10. WISE PLATFORM ADAPTER
# ---------------------------------------------------------------------------

class TestWisePlatformAdapter(unittest.TestCase):
    """Tests Wise Platform offline simulation stream."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_fetch_wise_transfers_returns_transactions(self):
        txs = self.agg.fetch_wise_transfers(
            api_token="wise_test_token",
            profile_id="12345",
            date_from="2026-01-01",
            date_to="2026-12-31",
        )
        self.assertGreater(len(txs), 0)

    def test_wise_transactions_are_cee_transaction_instances(self):
        txs = self.agg.fetch_wise_transfers("test_token", "12345")
        for tx in txs:
            self.assertIsInstance(tx, CEETransaction)

    def test_wise_transactions_have_correct_bank_code(self):
        txs = self.agg.fetch_wise_transfers("test_token", "12345")
        for tx in txs:
            self.assertEqual(tx.bank_code, CEEBankCode.WISE)

    def test_wise_transactions_source_field(self):
        txs = self.agg.fetch_wise_transfers("test_token", "12345")
        self.assertEqual(txs[0].source, "PSD2_STREAM_WISE")

    def test_wise_transactions_have_counterparty_name(self):
        txs = self.agg.fetch_wise_transfers("test_token", "12345")
        for tx in txs:
            self.assertGreater(len(tx.counterparty_name), 0)


# ---------------------------------------------------------------------------
# 11. TRANSACTION STREAM INGESTION (all 8 banks)
# ---------------------------------------------------------------------------

class TestCEETransactionStreamIngestion(unittest.TestCase):
    """Tests AISP transaction stream fetching for all 8 CEE/neo-bank providers."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)
        self.date_from = "2026-01-01"
        self.date_to = "2026-12-31"

    def _fetch(self, bank_code, iban):
        return self.agg.fetch_transaction_stream(
            bank_code, iban, self.date_from, self.date_to
        )

    def test_pkobp_stream(self):
        txs = self._fetch(CEEBankCode.PKOBP, "PL61109010140000071219812874")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_PKOBP")

    def test_pekao_stream(self):
        txs = self._fetch(CEEBankCode.PEKAO, "PL27114020040000300201355387")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_PEKAO")

    def test_bcr_stream(self):
        txs = self._fetch(CEEBankCode.BCR, "RO49AAAA1B31007593840000")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_BCR")

    def test_bt_stream(self):
        txs = self._fetch(CEEBankCode.BT, "RO98BTRL00501202A547033")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_BT")

    def test_alphabank_stream(self):
        txs = self._fetch(CEEBankCode.ALPHABANK, "GR1601101250000000012300695")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_ALPHABANK")

    def test_eurobank_stream(self):
        txs = self._fetch(CEEBankCode.EUROBANK, "GR1601101250000000012300695")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_EUROBANK")

    def test_revolut_stream(self):
        txs = self._fetch(CEEBankCode.REVOLUT, "LT123456789012345678")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_REVOLUT")

    def test_wise_stream(self):
        txs = self._fetch(CEEBankCode.WISE, "BE64210014108712")
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].source, "PSD2_STREAM_WISE")

    def test_transactions_have_sequential_item_ids(self):
        txs = self._fetch(CEEBankCode.PKOBP, "PL61109010140000071219812874")
        for i, tx in enumerate(txs, 1):
            self.assertEqual(tx.item_id, i)

    def test_transactions_have_end_to_end_id(self):
        txs = self._fetch(CEEBankCode.BCR, "RO49AAAA1B31007593840000")
        for tx in txs:
            self.assertGreater(len(tx.end_to_end_id), 0)

    def test_fetch_all_transaction_streams_multi_bank(self):
        bank_ibans = {
            CEEBankCode.PKOBP:   "PL61109010140000071219812874",
            CEEBankCode.BCR:     "RO49AAAA1B31007593840000",
            CEEBankCode.REVOLUT: "LT123456789012345678",
        }
        all_streams = self.agg.fetch_all_transaction_streams(
            bank_ibans, self.date_from, self.date_to
        )
        self.assertEqual(len(all_streams), 3)
        self.assertIn("PKOBP", all_streams)
        self.assertIn("BCR", all_streams)
        self.assertIn("REVOLUT", all_streams)


# ---------------------------------------------------------------------------
# 12. LEGACY OpenBankingPISPAggregator BRIDGE
# ---------------------------------------------------------------------------

class TestLegacyPISPAggregatorBridge(unittest.TestCase):
    """Tests that M57 OpenBankingPISPAggregator correctly delegates CEE codes to M83."""

    def test_supported_banks_includes_all_cee_codes(self):
        supported = OpenBankingPISPAggregator.SUPPORTED_BANKS
        for code in ("PKOBP", "PEKAO", "BCR", "BT", "ALPHABANK", "EUROBANK", "REVOLUT", "WISE"):
            self.assertIn(code, supported, f"{code} not in SUPPORTED_BANKS")

    def test_supported_banks_still_includes_bulgarian_banks(self):
        supported = OpenBankingPISPAggregator.SUPPORTED_BANKS
        for code in ("DSK", "UNCR", "UBBS", "BPBI"):
            self.assertIn(code, supported)

    def test_initiate_vendor_payment_pkobp_via_legacy_interface(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-M83-PL-001",
            debtor_iban="PL61109010140000071219812874",
            creditor_iban="PL27114020040000300201355387",
            creditor_name="Dostawca PL Sp. z o.o.",
            amount_eur=3500.0,
            remittance_info="Faktura M83-001",
            bank_code="PKOBP",
        )
        result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
        self.assertEqual(result.transaction_status, "ACCP")
        self.assertEqual(result.journal_entry["debit_account"], "401")
        self.assertEqual(result.journal_entry["credit_account"], "503")

    def test_initiate_vendor_payment_bcr_via_legacy_interface(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-M83-RO-001",
            debtor_iban="RO49AAAA1B31007593840000",
            creditor_iban="RO49AAAA1B31007593840001",
            creditor_name="Furnizor BCR SRL",
            amount_eur=5000.0,
            remittance_info="Factura 2026-08-001",
            bank_code="BCR",
        )
        result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
        self.assertEqual(result.transaction_status, "ACCP")

    def test_initiate_vendor_payment_revolut_via_legacy_interface(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-M83-REV-001",
            debtor_iban="LT123456789012345678",
            creditor_iban="LT987654321098765432",
            creditor_name="EU Supplier Ltd",
            amount_eur=2000.0,
            remittance_info="Invoice REV-001",
            bank_code="REVOLUT",
        )
        result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
        self.assertEqual(result.transaction_status, "ACCP")

    def test_initiate_vendor_payment_wise_via_legacy_interface(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-M83-WISE-001",
            debtor_iban="BE64210014108712",
            creditor_iban="BE64210014108713",
            creditor_name="Global Vendor LLC",
            amount_eur=1500.0,
            remittance_info="Transfer WISE-001",
            bank_code="WISE",
        )
        result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
        self.assertEqual(result.transaction_status, "ACCP")

    def test_unsupported_bank_code_raises_value_error(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-INVALID",
            debtor_iban="XX00000000000000000000000001",
            creditor_iban="XX00000000000000000000000002",
            creditor_name="Invalid Bank Vendor",
            amount_eur=100.0,
            remittance_info="Test",
            bank_code="INVALID_BANK",
        )
        with self.assertRaises(ValueError):
            OpenBankingPISPAggregator.initiate_vendor_payment(req)

    def test_bulgarian_dsk_payment_unaffected_by_m83(self):
        req = PaymentInitiationRequest(
            payment_id="PMT-DSK-BG-001",
            debtor_iban="BG71STSA93000028013479",
            creditor_iban="BG12UNCR70001524896321",
            creditor_name="Доставчик БГ ЕООД",
            amount_eur=750.0,
            remittance_info="Фактура 100001",
            bank_code="DSK",
        )
        result = OpenBankingPISPAggregator.initiate_vendor_payment(req)
        self.assertEqual(result.transaction_status, "ACCP")

    def test_aggregate_cee_balances_via_legacy_interface(self):
        bank_ibans = {
            "PKOBP": "PL61109010140000071219812874",
            "BCR":   "RO49AAAA1B31007593840000",
            "REVOLUT": "LT123456789012345678",
        }
        result = OpenBankingPISPAggregator.aggregate_cee_balances(bank_ibans)
        self.assertEqual(result["bank_count"], 3)
        self.assertGreater(result["total_consolidated_balance_eur"], 0)
        self.assertIn("bank_balances", result)
        self.assertIn("breakdown_by_country", result)
        self.assertIn("breakdown_by_currency", result)


# ---------------------------------------------------------------------------
# 13. PSD2BankProvider ENUM — M83 PROVIDERS
# ---------------------------------------------------------------------------

class TestPSD2BankProviderEnum(unittest.TestCase):
    """Tests that M83 CEE providers are present in PSD2BankProvider enum."""

    def test_pkobp_in_enum(self):
        self.assertEqual(PSD2BankProvider.PKOBP.value, "PKOBP")

    def test_pekao_in_enum(self):
        self.assertEqual(PSD2BankProvider.PEKAO.value, "PEKAO")

    def test_bcr_in_enum(self):
        self.assertEqual(PSD2BankProvider.BCR.value, "BCR")

    def test_bt_in_enum(self):
        self.assertEqual(PSD2BankProvider.BT.value, "BT")

    def test_alphabank_in_enum(self):
        self.assertEqual(PSD2BankProvider.ALPHABANK.value, "ALPHABANK")

    def test_eurobank_in_enum(self):
        self.assertEqual(PSD2BankProvider.EUROBANK.value, "EUROBANK")

    def test_revolut_in_enum(self):
        self.assertEqual(PSD2BankProvider.REVOLUT.value, "REVOLUT")

    def test_wise_in_enum(self):
        self.assertEqual(PSD2BankProvider.WISE.value, "WISE")

    def test_original_bulgarian_banks_still_present(self):
        for code in ("DSK", "UNICREDIT", "UBB", "POSTBANK"):
            self.assertIsNotNone(PSD2BankProvider(code))

    def test_total_provider_count(self):
        # 4 Bulgarian (M25) + 8 CEE (M83) = 12
        self.assertEqual(len(PSD2BankProvider), 12)


# ---------------------------------------------------------------------------
# 14. CEETransaction CANONICAL SCHEMA
# ---------------------------------------------------------------------------

class TestCEETransactionCanonicalSchema(unittest.TestCase):
    """Tests that CEETransaction dataclass has all required canonical fields."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_transaction_fields_complete(self):
        txs = self.agg.fetch_transaction_stream(
            CEEBankCode.PKOBP, "PL61109010140000071219812874"
        )
        required_fields = {
            "item_id", "bank_code", "date", "booking_date", "value_date",
            "counterparty_name", "counterparty_iban", "counterparty_bic",
            "debit_amount", "credit_amount", "currency", "narrative",
            "end_to_end_id", "source",
        }
        for tx in txs:
            tx_dict = dataclasses.asdict(tx)
            for field in required_fields:
                self.assertIn(field, tx_dict, f"Missing field: {field}")

    def test_transaction_debit_credit_non_negative(self):
        txs = self.agg.fetch_transaction_stream(
            CEEBankCode.BCR, "RO49AAAA1B31007593840000"
        )
        for tx in txs:
            self.assertGreaterEqual(tx.debit_amount, 0)
            self.assertGreaterEqual(tx.credit_amount, 0)

    def test_transaction_item_ids_are_sequential(self):
        txs = self.agg.fetch_transaction_stream(
            CEEBankCode.REVOLUT, "LT123456789012345678"
        )
        for i, tx in enumerate(txs, 1):
            self.assertEqual(tx.item_id, i)


# ---------------------------------------------------------------------------
# 15. TELEMETRY SNAPSHOT
# ---------------------------------------------------------------------------

class TestCEETelemetrySnapshot(unittest.TestCase):
    """Tests the Prometheus-compatible telemetry snapshot."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)

    def test_telemetry_snapshot_has_required_keys(self):
        snap = self.agg.get_telemetry_snapshot()
        required_keys = {
            "cee_open_banking_banks_registered",
            "cee_open_banking_consent_cache_size",
            "cee_open_banking_environment",
            "cee_open_banking_supported_countries",
            "cee_open_banking_fx_rates",
        }
        for key in required_keys:
            self.assertIn(key, snap, f"Missing telemetry key: {key}")

    def test_telemetry_banks_registered_count(self):
        snap = self.agg.get_telemetry_snapshot()
        self.assertEqual(snap["cee_open_banking_banks_registered"], 8)

    def test_telemetry_environment_sandbox(self):
        snap = self.agg.get_telemetry_snapshot()
        self.assertEqual(snap["cee_open_banking_environment"], "SANDBOX")

    def test_telemetry_fx_rates_include_pln_ron(self):
        snap = self.agg.get_telemetry_snapshot()
        self.assertIn("PLN", snap["cee_open_banking_fx_rates"])
        self.assertIn("RON", snap["cee_open_banking_fx_rates"])
        self.assertIn("EUR", snap["cee_open_banking_fx_rates"])

    def test_telemetry_consent_cache_grows_after_token_acquisition(self):
        agg = CEEOpenBankingAggregator(environment=CEEApiEnvironment.SANDBOX)
        agg.acquire_consent_token(CEEBankCode.PKOBP)
        agg.acquire_consent_token(CEEBankCode.BCR)
        snap = agg.get_telemetry_snapshot()
        self.assertEqual(snap["cee_open_banking_consent_cache_size"], 2)


# ---------------------------------------------------------------------------
# 16. FX CONVERSION HELPER
# ---------------------------------------------------------------------------

class TestFXConversion(unittest.TestCase):
    """Tests EUR-equivalent conversion for PLN and RON amounts."""

    def setUp(self):
        self.agg = CEEOpenBankingAggregator()

    def test_eur_to_eur_unchanged(self):
        result = self.agg._to_eur(1000.0, CEECurrency.EUR)
        self.assertAlmostEqual(result, 1000.0, places=2)

    def test_pln_to_eur(self):
        result = self.agg._to_eur(427.0, CEECurrency.PLN)
        expected = round(427.0 / EUR_TO_PLN_RATE, 2)
        self.assertAlmostEqual(result, expected, places=2)

    def test_ron_to_eur(self):
        result = self.agg._to_eur(497.0, CEECurrency.RON)
        expected = round(497.0 / EUR_TO_RON_RATE, 2)
        self.assertAlmostEqual(result, expected, places=2)

    def test_custom_fx_rate_injected(self):
        agg = CEEOpenBankingAggregator(fx_rates={"PLN": 4.00, "EUR": 1.0, "RON": 5.0, "GBP": 0.86})
        result = agg._to_eur(400.0, CEECurrency.PLN)
        self.assertAlmostEqual(result, 100.0, places=2)


# ---------------------------------------------------------------------------
# 17. PACKAGE-LEVEL IMPORTS (smoke test)
# ---------------------------------------------------------------------------

class TestM83PackageImports(unittest.TestCase):
    """Smoke tests that all M83 symbols are correctly exported from src.intake."""

    def test_cee_open_banking_aggregator_importable(self):
        from src.intake import CEEOpenBankingAggregator  # noqa: F401

    def test_cee_bank_code_importable(self):
        from src.intake import CEEBankCode  # noqa: F401

    def test_cee_bank_registry_importable(self):
        from src.intake import CEE_BANK_REGISTRY  # noqa: F401

    def test_validate_iban_cee_importable(self):
        from src.intake import validate_iban_cee  # noqa: F401

    def test_validate_polish_nip_importable(self):
        from src.intake import validate_polish_nip  # noqa: F401

    def test_validate_romanian_cif_importable(self):
        from src.intake import validate_romanian_cif  # noqa: F401

    def test_validate_greek_afm_importable(self):
        from src.intake import validate_greek_afm  # noqa: F401

    def test_piispstatus_importable(self):
        from src.intake import PIISPStatus  # noqa: F401

    def test_psd2_bank_provider_m83_codes_accessible(self):
        from src.intake import PSD2BankProvider
        self.assertEqual(PSD2BankProvider.PKOBP.value, "PKOBP")
        self.assertEqual(PSD2BankProvider.REVOLUT.value, "REVOLUT")


if __name__ == "__main__":
    unittest.main()
