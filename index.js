const express = require('express');
const router = express.Router();

const phoneRoutes = require('./phone');
const sosRoutes = require('./sos');
const threatRoutes = require('./threats');
const courseRoutes = require('./courses');
const systemRoutes = require('./system');

router.use('/phone', phoneRoutes);
router.use('/sos', sosRoutes);
router.use('/threats', threatRoutes);
router.use('/courses', courseRoutes);
router.use('/system', systemRoutes);

const loyaltyRoutes = require('./loyalty');
const scanRoutes = require('./scan');

router.use('/loyalty', loyaltyRoutes);
router.use('/scan', scanRoutes);

module.exports = router;
