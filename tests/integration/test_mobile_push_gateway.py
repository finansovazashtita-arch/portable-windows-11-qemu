"""
Unit tests for Native Mobile Push Notification Gateway Engine.
"""

import unittest

from src.integration.mobile_push_gateway import MobilePushGateway, MobilePushNotification, PushPriority, PushProvider


class TestMobilePushGateway(unittest.TestCase):
    """Test suite for MobilePushGateway."""

    def test_send_push_apns_success(self):
        notif = MobilePushNotification(
            device_token="apns_token_ios_998123456789",
            title="🚨 КРИТИЧНА ИЗМАМА",
            body="Неоторизирана промяна на IBAN сметка!",
            provider=PushProvider.APPLE_APNS,
            priority=PushPriority.CRITICAL,
        )
        res = MobilePushGateway.send_push_notification(notif)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["provider"], "APPLE_APNS")

    def test_send_push_fcm_success(self):
        notif = MobilePushNotification(
            device_token="fcm_token_android_887123456789",
            title="⚠️ HA Failover Alert",
            body="macmini-primary е прехвърлен към secondary.",
            provider=PushProvider.FIREBASE_FCM,
            priority=PushPriority.HIGH,
        )
        res = MobilePushGateway.send_push_notification(notif)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["provider"], "FIREBASE_FCM")


if __name__ == "__main__":
    unittest.main()
