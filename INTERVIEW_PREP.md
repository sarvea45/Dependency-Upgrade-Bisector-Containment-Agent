# Celesto Founder 1:1 Interview Preparation Guide

This document contains talking points and architectural justifications prepared for the Celesto Founder 1:1 interview round.

---

## 1. Why Celesto and not Docker or E2B?

### The Kernel Boundary Argument
* **Docker / Containers**: Containers share the host Linux kernel (`/proc`, `/sys`, syscall dispatch table). Any kernel vulnerability, unpatched CVE, or root privilege escalation inside an untrusted container can escape to the host. Furthermore, Docker cannot take sub-second full-memory snapshots (CPU registers + RAM + filesystem state).
* **E2B**: E2B is proprietary, cloud-hosted only, Linux-only, and closed-box. It lacks local offline execution for developers without cloud connectivity.
* **Celesto Advantage**: Celesto provides open-source microVM hardware isolation (Firecracker/QEMU) where each guest has its own dedicated kernel. It delivers container-like startup speeds (~500ms) with true hardware-level VM isolation, supports identical local and cloud APIs, supports Windows and macOS guests, and enables instant point-in-time snapshot rollbacks.

---

## 2. What would break at 1,000 concurrent users?

### Bottleneck Analysis & Engineering Mitigations
1. **Host TAP Interface & Vsock Exhaustion**:
   * *Problem*: Linux hosts typically limit active TAP interfaces and vsock channel allocations (~1024).
   * *Mitigation*: Implement dynamic microVM worker pooling with aggressive TTLs and instant teardown upon completion.
2. **NVMe / Disk I/O Saturation during Snapshots**:
   * *Problem*: 1,000 simultaneous snapshot writes saturate storage bandwidth.
   * *Mitigation*: Utilize copy-on-write (CoW) thin provisioning and rate-limit concurrent snapshot creation using worker queues.
3. **Database Connection Saturation**:
   * *Problem*: 1,000 concurrent agent runs hammering PostgreSQL with step updates will exhaust the default connection pool.
   * *Mitigation*: Deploy PgBouncer for transaction-level connection pooling and batch command audit writes asynchronously.

---

## 3. One Piece of Honest Product Feedback for the Founder

> **Observability during Local Vsock Handshakes**:
> During local development under heavy CPU contention, vsock connection handshakes between host and guest occasionally timed out before emitting granular boot error codes (defaulting to a generic socket closed exception). Providing an explicit `BootState` event stream (`kernel_loaded` $\rightarrow$ `guest_agent_listening`) would make debugging local edge cases significantly faster for developers.

---

## 4. Key Numbers to Know by Heart

* **Evaluated Runs**: 20 consecutive, end-to-end fresh runs.
* **Success Rate**: 85.0% (17 succeeded, 3 controlled failure post-mortems).
* **Median Wall-Clock Time**: 13.2250s (mean of 10th and 11th sorted runs).
* **P90 Wall-Clock Time**: 16.2000s (18th sorted run).
* **Median Boot-to-Ready Time**: 0.5350s.
* **Total Compute Cost**: $0.01109 USD.
* **Step 7 Snapshot Rollback Latency**: <250ms (vs. 15+ seconds for a clean-slate container rebuild).
