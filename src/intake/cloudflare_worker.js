/**
 * Cloudflare Email Routing Worker for Microinvest Bank Statement OCR Automation.
 *
 * Intercepts incoming emails sent to statements@finansprotect.com / statements@openbalancer.com,
 * extracts PDF statement attachments, and forwards them to the n8n OCR webhook pipeline.
 */

export default {
  async email(message, env, ctx) {
    const sender = message.from;
    const recipient = message.to;
    const subject = message.headers.get("subject") || "Bank Statement Email Intake";
    const messageId = message.headers.get("message-id") || `msg_${Date.now()}`;

    console.log(`Received email from: ${sender} to: ${recipient} with subject: ${subject}`);

    // Read raw email stream
    const rawEmail = await new Response(message.raw).text();

    const webhookUrl = env.MICROINVEST_N8N_WEBHOOK_URL || "http://100.83.83.8:5679/webhook/microinvest-ocr";

    const payload = {
      source: "CLOUDFLARE_EMAIL_ROUTING",
      sender: sender,
      recipient: recipient,
      subject: subject,
      message_id: messageId,
      raw_mime_base64: btoa(rawEmail),
      received_at: new Date().toISOString(),
    };

    try {
      const response = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Cloudflare-Email-Signature": env.CF_INTAKE_SECRET || "finansprotect-secret-key",
        },
        body: JSON.stringify(payload),
      });

      console.log(`Webhook response status: ${response.status}`);
    } catch (err) {
      console.error(`Failed to post email payload to n8n webhook: ${err}`);
    }
  },
};
