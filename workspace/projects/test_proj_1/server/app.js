const http = require('http');
const server = http.createServer((req, res) => {
  res.writeHead(200, {'Content-Type': 'text/plain'});
  res.end('Hello AiON Sandbox Engine!');
});
server.listen(process.env.PORT, () => console.log('Server running!'));