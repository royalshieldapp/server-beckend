const express = require('express');
const router = express.Router();

// POST /api/sos/alert
router.post('/alert', async (req, res) => {
    const { location, type, contacts } = req.body;

    console.log('Received SOS Alert:', { location, type });

    // TODO: Integrate Twilio here to send SMS/Call
    // const client = require('twilio')(accountSid, authToken);
    // await client.messages.create({ ... });

    // For now, acknowledge receipt
    res.json({
        success: true,
        message: 'SOS Alert received and processing',
        incidentId: 'INC-' + Date.now()
    });
});

module.exports = router;
