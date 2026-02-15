const express = require('express');
const router = express.Router();

// GET /api/courses
router.get('/', (req, res) => {
    const courses = [
        {
            id: 'c1',
            title: 'Cybersecurity Basics',
            description: 'Protect yourself from online threats.',
            duration: '45 min',
            level: 'Beginner',
            videoUrl: '', // Add real URLs if available
            thumbnailUrl: ''
        },
        {
            id: 'c2',
            title: 'Phishing Awareness',
            description: 'How to spot fake emails and SMS.',
            duration: '30 min',
            level: 'Intermediate'
        },
        {
            id: 'c3',
            title: 'Network Security',
            description: 'Securing your home Wi-Fi.',
            duration: '60 min',
            level: 'Advanced'
        }
    ];

    res.json({ courses });
});

module.exports = router;
