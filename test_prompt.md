Conduct a full end-to-end technical and functional audit of the ArmGuard application.

Context:
ArmGuard is a Django-based military armory management system with a modular architecture (admin, personnel, inventory, transactions) and an existing test suite with ~92% pass rate. The goal is to re-test, re-evaluate, and produce an updated comprehensive analysis report that covers architecture, UX, performance, scalability, and modernization readiness.

Your task is to simulate a senior QA engineer + security auditor + product architect reviewing the entire application.

---

SECTION 1 — FUNCTIONAL VERIFICATION

• Re-test all core features:
  - Personnel registration & management
  - Inventory lifecycle
  - Transaction issuing/return workflows
  - Role-based access controls
  - Admin panel functionality
  - Reporting and search features

• Identify:
  - Broken workflows
  - Edge-case failures
  - Redundant logic
  - Missing validation
  - Data consistency issues

• Verify integrations:
  - Database operations
  - External services
  - APIs
  - middleware behaviors
  - deployment scripts

Output:
✔ functional coverage status
✔ failure list
✔ risk severity for each issue

---

SECTION 2 — USABILITY & UX EVALUATION

Evaluate the application from a first-time military user perspective:

• Navigation clarity
• Form usability
• Data entry efficiency
• Accessibility compliance
• Mobile responsiveness
• Workflow friction
• Visual hierarchy
• Feedback and error messaging

Simulate use on:
- Desktop
- Tablet
- Mobile browser

Output:
✔ usability score (1–10)
✔ UX pain points
✔ modernization recommendations
✔ mobile readiness assessment

---

SECTION 3 — PERFORMANCE TESTING

Measure:

• Page load times
• Database query efficiency
• Resource usage
• Static file handling
• Concurrent user behavior
• Stress/load behavior
• caching effectiveness

Identify:

• backend bottlenecks
• frontend rendering delays
• scaling risks

Output:
✔ performance metrics
✔ bottleneck list
✔ optimization recommendations

---

SECTION 4 — SECURITY AUDIT

Audit:

• authentication & authorization
• session handling
• brute force protection
• CSRF/XSS/SQL injection defenses
• file upload safety
• permission escalation risks
• data leakage risks
• logging & audit trail integrity

Simulate attack scenarios and describe exposure.

Output:
✔ security rating (1–10)
✔ vulnerability list
✔ severity ranking
✔ mitigation plan

---

SECTION 5 — RELIABILITY & STABILITY

Evaluate:

• error recovery behavior
• logging coverage
• crash handling
• data integrity protection
• backup/restore processes
• deployment resilience

Output:
✔ reliability score
✔ failure scenarios
✔ recovery readiness

---

SECTION 6 — MAINTAINABILITY

Review codebase:

• modularity
• documentation quality
• test coverage
• CI/CD readiness
• technical debt
• refactoring needs

Output:
✔ maintainability score
✔ refactor priority list
✔ long-term risks

---

SECTION 7 — SCALABILITY

Assess architecture for:

• horizontal scaling
• database growth
• concurrency
• caching strategies
• async/background processing
• load balancing readiness

Output:
✔ scalability score
✔ growth limits
✔ architecture upgrade recommendations

---

SECTION 8 — USER FEEDBACK SIMULATION

Simulate feedback from:

• armory staff
• commanders
• administrators

Identify:

• operational pain points
• training friction
• workflow inefficiencies

Output:
✔ summarized user sentiment
✔ improvement opportunities

---

FINAL DELIVERABLE

Generate an updated structured report with:

1. Executive Summary
2. Category-by-category findings
3. Prioritized fix roadmap
4. Risk assessment
5. Deployment readiness score
6. Modernization readiness score
7. Overall grade

Use clear headings, severity labels, and actionable recommendations.

Focus on practical improvements, not theoretical ones.

