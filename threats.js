const express = require('express');
const router = express.Router();

// GET /api/threats?lat=...&lng=...
router.get('/', (req, res) => {
    const { lat, lng } = req.query;

    // Return dummy threat data centered around the user
    // In production, fetch from a real threat intel feed

    const baseLat = parseFloat(lat) || 40.7128;
    const baseLng = parseFloat(lng) || -74.0060;

    const threats = [
        {
            id: 't1',
            type: 'Botnet',
            lat: baseLat + 0.01,
            lng: baseLng + 0.01,
            severity: 'HIGH',
            description: 'Active Mirai Botnet Node'
        },
        {
            id: 't2',
            type: 'Phishing',
            lat: baseLat - 0.005,
            lng: baseLng - 0.005,
            severity: 'MEDIUM',
            description: 'SMS Phishing Campaign Source'
        },
        {
            id: 't3',
            type: 'Malware',
            lat: baseLat + 0.015,
            lng: baseLng - 0.01,
            severity: 'LOW',
            description: 'Adware Distribution Server'
        }
    ];

    res.json({ threats });
});

module.exports = router;
