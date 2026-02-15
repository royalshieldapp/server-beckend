const express = require('express');
const router = express.Router();

let userPoints = 1250; // Mock database
let userTier = 'Gold';

// GET /api/loyalty/status
router.get('/status', (req, res) => {
    res.json({
        points: userPoints,
        tier: userTier,
        nextTier: 'Platinum',
        pointsToNextTier: 5000 - userPoints
    });
});

// POST /api/loyalty/points
router.post('/points', (req, res) => {
    const { action, points } = req.body;

    if (!points) {
        return res.status(400).json({ error: 'Points value required' });
    }

    userPoints += points;

    // Simple tier logic
    if (userPoints > 5000) userTier = 'Platinum';
    else if (userPoints > 1000) userTier = 'Gold';
    else if (userPoints > 200) userTier = 'Silver';
    else userTier = 'Bronze';

    res.json({
        success: true,
        message: `Added ${points} points for ${action}`,
        newTotal: userPoints,
        currentTier: userTier
    });
});

module.exports = router;
