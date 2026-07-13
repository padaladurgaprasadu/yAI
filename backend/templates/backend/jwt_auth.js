const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');

const JWT_SECRET = process.env.JWT_SECRET || 'fallback_secret_key_change_in_production';

// Mock DB for template purposes - replace with actual DB connection
const users = [];

const register = async (req, res) => {
    try {
        const { email, password } = req.body;
        
        // Check if user exists
        if (users.find(u => u.email === email)) {
            return res.status(400).json({ error: 'User already exists' });
        }

        // Hash password
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password, salt);

        const newUser = {
            id: Date.now().toString(),
            email,
            password: hashedPassword
        };
        
        users.push(newUser);
        
        const token = jwt.sign({ id: newUser.id, email: newUser.email }, JWT_SECRET, { expiresIn: '1d' });
        
        res.status(201).json({ token, user: { id: newUser.id, email: newUser.email } });
    } catch (error) {
        console.error("Registration error:", error);
        res.status(500).json({ error: 'Internal server error' });
    }
};

const login = async (req, res) => {
    try {
        const { email, password } = req.body;
        
        const user = users.find(u => u.email === email);
        if (!user) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const validPassword = await bcrypt.compare(password, user.password);
        if (!validPassword) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '1d' });
        
        res.json({ token, user: { id: user.id, email: user.email } });
    } catch (error) {
        console.error("Login error:", error);
        res.status(500).json({ error: 'Internal server error' });
    }
};

const verifyToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) return res.status(401).json({ error: 'Access denied' });
    
    try {
        const verified = jwt.verify(token, JWT_SECRET);
        req.user = verified;
        next();
    } catch (error) {
        res.status(400).json({ error: 'Invalid token' });
    }
};

module.exports = { register, login, verifyToken };
