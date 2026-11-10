module.exports = {
  apps: [
    {
      name: "auto-clipper-bot",
      script: ".venv/bin/python3",
      args: "main.py",
      cwd: "./",
      interpreter: "none",
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
