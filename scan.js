const express = require('express');
const router = express.Router();
const axios = require('axios');

// POST /api/scan/url
router.post('/url', async (req, res) => {
    const { url } = req.body;
    const apiKey = process.env.VIRUSTOTAL_API_KEY;

    if (!url) {
        return res.status(400).json({ error: 'URL is required' });
    }

    if (!apiKey) {
        console.warn('VirusTotal API Key missing in environment');
        // Fallback or error
        return res.status(503).json({ error: 'Scanner service configuration unavailable' });
    }

    try {
        // 1. Submit URL for scanning
        const scanResponse = await axios.post(
            'https://www.virustotal.com/api/v3/urls',
            `url=${encodeURIComponent(url)}`,
            {
                headers: {
                    'x-apikey': apiKey,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            }
        );

        const analysisId = scanResponse.data.data.id;

        // 2. Poll for results (Simplified: just returning ID for client to poll or wait)
        // In a real implementation, we might wait or use a callback.
        // For this demo, let's just return the analysis link ID.

        res.json({
            success: true,
            analysisId: analysisId,
            message: 'URL submitted for scanning'
        });

    } catch (error) {
        console.error('VirusTotal API Error:', error.response ? error.response.data : error.message);
        res.status(500).json({ error: 'Failed to scan URL via VirusTotal' });
    }
});

module.exports = router;
