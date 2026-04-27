# Lab: From "Works on My Machine" to Containers

**Course:** Cloud Computing, Chapter 5 – Container

| | Content |
|---|---|
| **Onsite Session** | Parts A, B, C – hands-on Docker work |
| **Take-home Homework** | Parts D, E, F – deeper exploration + reflection |

In this lab you package a real multi-container application using Docker, explore how container networking solves the service-discovery problem, and analyse when managed container services are the right tool.

---

## Prerequisites – complete before the session

- **Docker Desktop** installed and running. Check:
  ```bash
  docker version
  docker compose version
  ```
  Both commands must succeed. If Docker is not installed, use the official guide at https://docs.docker.com/get-docker/.
- **Git** installed.
- A basic code editor (VS Code recommended).
- Clone or copy the `05_Container/` folder from the course repository to a local path you can work in.

**Pre-lab Questions** *(hand in at the start of the session)*

- H1: What version of Docker Engine and Docker Compose is installed on your machine?
- H2: The lecture lists six key benefits of containers. Choose **three** you find most relevant for a software developer and explain in one sentence each why they matter in practice.
- H3: In your own words: what is the difference between a Docker **image** and a Docker **container**? Use an analogy.

---

## Onsite Session – Parts A, B, C

---

## Part A – Pull, Inspect, and Run Existing Containers (45 min)

Goal: Get comfortable with the Docker CLI, understand the image → container relationship, and observe the container lifecycle in action.

---

### A1 – Pull and run a ready-made container

```bash
# Pull the official nginx image (web server)
docker pull nginx:alpine

# Run it in detached mode, map host port 8000 to container port 80
docker run -d --name web -p 8000:80 nginx:alpine

# Verify it is running
docker ps
```

Open `http://localhost:8000` in your browser. You should see the nginx welcome page.

- **Q1:** In `docker ps` output, what is listed in the **PORTS** column for your container? Write it out and explain what each part (`0.0.0.0:8000->80/tcp`) means in terms of host and container networking.
- **Q2:** What does the `-d` flag do? What happens if you omit it?

---

### A2 – Explore the running container

```bash
# View live logs
docker logs web

# Execute a command inside the running container
docker exec -it web sh

# Inside the container, run:
cat /etc/os-release    # which OS is this?
hostname               # what is the container hostname?
ps aux                 # which processes are running?
exit
```

- **Q3:** What Linux distribution is running **inside** the container? What is the PID-1 process (the first process started)? Why does a container only run a single main process rather than a full init system?
- **Q4:** The nginx image is based on Alpine Linux, yet your host might be macOS or Windows. How is it possible to run an Alpine container on a non-Linux host? What layer of Docker makes this work?

---

### A3 – Inspect image layers

```bash
# Show the image layers that make up nginx:alpine
docker image inspect nginx:alpine --format '{{json .RootFS.Layers}}' | python3 -m json.tool

# Or using docker history for a human-readable view:
docker history nginx:alpine
```

- **Q5:** How many layers does the `nginx:alpine` image have? Based on the `docker history` output, what does each layer roughly correspond to (hint: look at the CREATED BY column)? What is the advantage of this layered approach when you have ten different services all based on the same base image?

---

### A4 – Container lifecycle

```bash
# Stop the container (sends SIGTERM, waits, then SIGKILL)
docker stop web

# Container is stopped but still exists – inspect it
docker ps -a

# Start it again
docker start web

# Remove a running container (force)
docker rm -f web

# Verify it is gone
docker ps -a
```

- **Q6:** After `docker stop`, is the container **deleted**? Where does it go? Sketch (in words or a small diagram) the container lifecycle states from the lecture: Created → Running → Stopped → Deleted.

---

## Part B – Write Your First Dockerfile (65 min)

Goal: Package the provided Python Flask application into a custom Docker image by completing the Dockerfile skeleton. Understand why instruction order affects build speed.

The application in `05_Container/app/` is a visit counter that uses Redis to persist the count. For now you will build the image without Redis – the app will show an error for the Redis connection, which is expected.

---

### B1 – Read the application code

Open `05_Container/app/app.py` and `05_Container/app/requirements.txt` in your editor.

- **Q7 (before writing anything):** Without running the code, answer these questions by reading the source:
  - Which port does the Flask app listen on?
  - Which environment variable controls the Redis hostname?
  - What does the `/health` endpoint return, and when does it return HTTP 503?

---

### B2 – Complete the Dockerfile skeleton

Open `05_Container/app/Dockerfile.skeleton`. Copy it to `05_Container/app/Dockerfile` and fill in all seven `TODO` blocks. Use the lecture slide **"Basic Dockerfile Structure"** as a reference.

```bash
cp 05_Container/app/Dockerfile.skeleton 05_Container/app/Dockerfile
# Now edit Dockerfile and replace every ___ placeholder
```

Hints:
- Base image: `python:3.12-slim`
- Working directory: `/app`
- Install command: `pip install --no-cache-dir -r requirements.txt`
- Application file: `app.py`
- Port: `5000`

---

### B3 – Build the image

```bash
cd 05_Container/app
docker build -t visitcounter:v1 .
```

Watch the build output carefully – each step corresponds to a Dockerfile instruction.

```bash
# Inspect the resulting image
docker images visitcounter:v1
docker history visitcounter:v1
```

- **Q8:** How large is your `visitcounter:v1` image (in MB)? How many layers does it have? Compare this size to the `nginx:alpine` image. What contributes most to the size?

---

### B4 – Run the image

```bash
docker run -d --name counter -p 8080:5000 visitcounter:v1
docker logs counter
```

Open `http://localhost:8080`. You will see a Redis error – that is expected because no Redis container is running yet.

- **Q9:** Rebuild the image after making a trivial change: open `app.py`, add a comment (`# test`) on any line, save, and rebuild with the **same tag** `visitcounter:v1`. Watch which steps say `CACHED` and which re-execute. Now repeat but change only `requirements.txt` (e.g. add a blank line). Which layers rebuild? Explain **why** the order `COPY requirements.txt` → `RUN pip install` → `COPY app.py` is intentional and beneficial for build speed.

---

### B5 – Clean up

```bash
docker rm -f counter
```

---

## Part C – Multi-Container Application with Docker Compose (55 min)

Goal: Connect the visit counter to Redis using Docker Compose, understand how Docker's built-in DNS resolves service names, and observe what a named volume does for data persistence.

---

### C1 – Complete the Docker Compose skeleton

Open `05_Container/docker-compose.skeleton.yml`. Copy it to `05_Container/docker-compose.yml` and fill in all seven `TODO` blocks.

```bash
cp 05_Container/docker-compose.skeleton.yml 05_Container/docker-compose.yml
# Edit docker-compose.yml and replace every ___ placeholder
```

Key decisions to make:
- Port mapping for the app: host `8080` → container `5000`
- `REDIS_HOST` environment variable: must be the **service name** `redis`, not an IP address
- Volume mount for Redis: named volume `redis_data` → `/data`
- Network: both services must share the same custom network `app_net`

---

### C2 – Start the stack

```bash
cd 05_Container
docker compose up --build -d

# Check all services are healthy
docker compose ps

# Stream logs from all services
docker compose logs -f
```

Open `http://localhost:8080`. Refresh several times and watch the visit counter increment.

- **Q10:** What does `docker compose ps` show for each service? Which column tells you if a service started correctly?

---

### C3 – Explore service discovery (no hardcoded IPs)

Docker's built-in DNS resolves service names to container IPs on custom networks.

```bash
# Open a shell inside the running app container
docker compose exec app sh

# Inside the container, test DNS resolution:
nslookup redis           # resolves the redis service name to its IP
ping -c 3 redis          # reachability check
wget -qO- redis:6379     # raw TCP probe (expect a Redis protocol error, not "connection refused")
exit
```

- **Q11:** What IP address did `nslookup redis` resolve to? Now stop and restart the Redis container and re-run `nslookup redis` from the app container:
  ```bash
  docker compose restart redis
  docker compose exec app sh -c "nslookup redis"
  ```
  Did the IP change? Did the service name still resolve? Why is this the correct approach to container-to-container communication instead of hardcoding IPs?

---

### C4 – Verify volume persistence

```bash
# Note the current visit count shown in the browser, then restart the app container
docker compose restart app

# Check the count again in the browser
```

- **Q12:** Did the visit count reset when you restarted the **app** container? Why or why not? Now restart the **redis** container:
  ```bash
  docker compose restart redis
  ```
  Did the count reset? What does the named volume `redis_data` do, and where does Docker store it on your host machine? Run `docker volume inspect 05_container_redis_data` (adjust the name if needed) to find out.

---

### C5 – Reflection questions (end of onsite session)

- **Q13:** The lecture slide "Containers vs. Virtual Machines" shows that containers share the host OS kernel while VMs each have their own Guest OS. Based on what you observed today: when you ran `cat /etc/os-release` inside the nginx container and it showed Alpine Linux, what was actually shared with the host and what was isolated? Be specific (kernel, filesystem, network stack, processes).

- **Q14:** The lecture lists **immutability** as a key container principle: containers are destroyed and recreated rather than modified in place. In this lab, you ran `docker rm -f counter` and recreated it. What happened to any changes you made inside the container? What is the **only** correct way to persist data across container restarts, and how did you implement it in this lab?

- **Q15:** Look at the `docker-compose.yml` you completed. The `app` service uses `depends_on: redis`. Does this guarantee that Flask can connect to Redis on the very first request? Why or why not? What would you add to a production-grade Compose file to handle this robustly?

---

## Take-home Homework – Parts D, E, F

---

## Part D – Network Isolation and Security (60 min)

Goal: Implement two separate networks (frontend and backend) to enforce the principle of least privilege between containers, and verify isolation by attempting blocked connections.

The lecture slide **"Network Isolation & Security"** shows a three-tier architecture where the public-facing nginx cannot reach the database directly. You will reproduce this pattern.

---

### D1 – Create an isolated network topology

Create a new file `05_Container/docker-compose.isolated.yml` with the following services and two networks:

- `frontend_net`: shared between `app` and a new `proxy` service (nginx)
- `backend_net`: shared between `app` and `redis`
- `redis` is **only** on `backend_net` – the proxy cannot reach it directly

Start from this skeleton and fill in the network assignments:

```yaml
services:

  proxy:
    image: nginx:alpine
    ports:
      - "8081:80"
    networks:
      - frontend_net
    # A real setup would use a custom nginx.conf to forward to app:5000

  app:
    build: ./app
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - redis
    networks:
      - frontend_net
      - backend_net  # app bridges both networks

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - backend_net  # redis only on the backend network

volumes:
  redis_data:

networks:
  frontend_net:
    driver: bridge
  backend_net:
    driver: bridge
```

Start the stack:
```bash
docker compose -f 05_Container/docker-compose.isolated.yml up -d
```

---

### D2 – Verify isolation

```bash
# From the proxy container: can it reach the app? (should succeed)
docker compose -f 05_Container/docker-compose.isolated.yml exec proxy \
  wget -qO- http://app:5000/health

# From the proxy container: can it reach redis directly? (should FAIL)
docker compose -f 05_Container/docker-compose.isolated.yml exec proxy \
  sh -c "ping -c 2 redis || echo 'Cannot reach redis – isolation working'"
```

- **Q16:** Did the isolation test confirm that `proxy` cannot reach `redis` directly? Paste the output of both commands. Which Docker mechanism enforces this separation – is it a firewall rule, a Linux kernel feature, or something else?

- **Q17:** Relate this isolation pattern to the lecture slide on **network security**. If the `proxy` container were compromised by an attacker, what damage could they do in this architecture, and what could they **not** do? How does this limit the blast radius compared to a setup where all containers share a single default network?

---

## Part E – Container Immutability and Data Persistence (45 min)

Goal: Prove the immutability principle by making a change inside a running container and observing that it is gone after a restart. Then use a bind mount to understand the difference between named volumes and host-path mounts.

---

### E1 – Demonstrate immutability

```bash
# Start the app container from Part C (if not already running)
cd 05_Container
docker compose up -d

# Write a file into the running container's filesystem
docker compose exec app sh -c "echo 'I was here' > /tmp/graffiti.txt"

# Verify the file exists
docker compose exec app cat /tmp/graffiti.txt

# Restart (stop + start) the container
docker compose restart app

# Check if the file survived
docker compose exec app sh -c "cat /tmp/graffiti.txt 2>/dev/null || echo 'File gone – immutability confirmed'"
```

- **Q18:** Did the file survive the restart? Explain **why** using the concept of the container's **writable layer** (also called the container layer). What is the relationship between the read-only image layers and this writable layer?

- **Q19:** Based on this experiment, explain in 3–5 sentences what the **immutability principle** means for how cloud-native applications should be designed. If you can never persist state inside a container, where should application state (user data, session data, configuration) live?

---

### E2 – Named volumes vs. bind mounts

In Part C, you used a **named volume** for Redis. Docker also supports **bind mounts** (mapping a host directory into the container).

Add a bind mount to the `app` service in your `docker-compose.yml` for development purposes:

```yaml
  app:
    build: ./app
    volumes:
      - ./app:/app   # bind mount: host directory → container /app
    ...
```

Bring the stack up again with this change, then edit `app/app.py` on your host (e.g., change the `<h1>` text). Refresh `http://localhost:8080`.

- **Q20:** Did your change appear without rebuilding the image? Explain why. Is a bind mount appropriate for **production** deployments? What are the trade-offs between bind mounts (for development) and named volumes (for production)?

---

## Part F – Managed Container Services: When to Use What? (60 min)

Goal: Apply the **"Positioning: When to Use What?"** decision tree from the lecture to real scenarios. You will not deploy anything – this is a written analysis exercise.

---

### F1 – Analyse three scenarios

For each scenario below, state which Azure managed container service you would choose (ACI, App Service for Containers, or AKS) and justify your answer in 4–6 sentences. Use the lecture's decision tree and the feature comparison tables.

**Scenario A – The Night-time Report Generator**  
A financial company runs a Python script every night at 02:00 that queries a database, generates a PDF report, and uploads it to Azure Blob Storage. The script takes about 8 minutes to run. It has no HTTP endpoint. It must not incur costs between runs.

- **Q21:** Which service would you choose for Scenario A? Justify your choice by naming at least two characteristics of your chosen service that match the requirements and at least one service you explicitly ruled out and why.

**Scenario B – The Customer-Facing REST API**  
A startup built a Node.js REST API for their mobile app. They expect 50–2,000 requests per minute depending on time of day. They need automatic HTTPS, want to deploy a new Docker image on every Git push to `main`, and cannot afford to hire a Kubernetes administrator.

- **Q22:** Which service would you choose for Scenario B? Justify your choice. Include what is managed **for you** by the platform and what remains **your responsibility** as the customer.

**Scenario C – The Microservices Platform**  
An e-commerce platform consists of 12 independent microservices (payment, inventory, recommendations, search, …) written in five different languages. Services communicate via gRPC and Kafka. The team needs blue-green deployments, automatic scaling per service, and full control over networking policies between services.

- **Q23:** Which service would you choose for Scenario C? Justify your choice. What would happen if you tried to run this on ACI instead? What specific ACI limitations would you hit first?

---

### F2 – Final reflection

- **Q24:** The lecture presents a **"Works on My Machine" problem** as the original motivation for containers. Based on everything you did in this lab, write 4–6 sentences describing concretely **how** the combination of a Dockerfile, a container image, and a registry solves this problem end-to-end. Reference specific steps from the lab.

- **Q25:** Compare the experience of running the visit counter application with Docker Compose to what it would take to run the same application on a **VM** (as in the previous IaaS lab). List at least three specific differences: what did Docker handle automatically that you would have had to do manually on a VM?

---

## Cleanup

When you are finished, remove all containers, networks, and volumes:

```bash
cd 05_Container
docker compose down -v
docker compose -f docker-compose.isolated.yml down -v
docker image rm visitcounter:v1 2>/dev/null || true
```

---

## Submission

Submit a single PDF or Markdown document containing:

1. Your answers to H1–H3 (pre-lab questions).
2. Your answers to Q1–Q25 (lab questions, in order).
3. Your completed `Dockerfile` (Part B) and `docker-compose.yml` (Part C) as code blocks.
4. The output of `docker compose ps` from Part C and the isolation test output from Part D.

Each written answer should be **3–6 sentences**. Code questions require exact output or code snippets.

---

## Quick Command Reference

| Task | Command |
|---|---|
| List running containers | `docker ps` |
| List all containers (incl. stopped) | `docker ps -a` |
| Build an image from Dockerfile | `docker build -t name:tag .` |
| Run a container (detached, port mapped) | `docker run -d -p host:container image` |
| Open a shell in a running container | `docker exec -it name sh` |
| View logs | `docker logs name` |
| Stop and remove a container | `docker rm -f name` |
| Start all Compose services | `docker compose up --build -d` |
| Stop all Compose services | `docker compose down` |
| Stop and remove volumes too | `docker compose down -v` |
| Open shell via Compose | `docker compose exec service sh` |
| Show image size and history | `docker history image` |
| Inspect a named volume | `docker volume inspect volume_name` |
