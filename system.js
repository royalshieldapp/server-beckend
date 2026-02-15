const express = require('express');
const router = express.Router();

// GET /api/system/status
router.get('/status', (req, res) => {
    res.json({
        status: 'OPERATIONAL',
        services: {
            database: 'CONNECTED',
            threatFeed: 'LIVE',
            smsGateway: 'READY',
            paymentSystem: 'ONLINE'
        },
        lastUpdate: new Date().toISOString()
    });
});

module.exports = router;
