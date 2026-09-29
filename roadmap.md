# Hackathon Roadmap

Detailed tasks, owners and timeline: `TASKS.md`.

## Phase 0: Pre-Hackathon Bootstrap
Status: DONE

- [x] Project structure, FastAPI skeleton, configuration, health endpoint
- [x] AIProvider abstraction, AIService, MockProvider, generic AI schemas
- [x] Basic tests (5/5 passing), documentation templates
- [x] Local run verification

## Phase 1: Theme Analysis
Status: DONE. Theme: Synthetic Data Platform (HackDataV2).

## Phase 2: Idea Generation
Status: DONE

## Phase 3: Idea Evaluation
Status: DONE

## Phase 4: Idea Selection
Status: DONE. Constraint-aware synthetic data studio (`idea.md`).

## Phase 5: MVP Lock
Status: DONE. Must-have / enhancements / cut are in `idea.md` and `TASKS.md`.

## Phase 6: Product & Architecture Specification
Status: DONE (`architecture.md`, `design.md`, `docs/api-contract.md` draft v0.1)

## Phase 7: Work Division
Status: DONE. Farhan = backend core, Haider = frontend + documents/export modules (`TASKS.md`).

## Phase 8: Implementation
Status: UNLOCKED / IN PROGRESS

- [ ] H0 contract freeze + scaffold (0:00–0:45)
- [ ] Core: template/CSV/prompt → schema → generate → preview → report (0:45–3:30)
- [ ] Differentiators: DB connect, scenarios + ground truth, invoice PDF, ZIP (4:00–6:00)

## Phase 9: Integration
Status: UNLOCKED (at the checkpoints)

- [ ] Checkpoint 1 (3:30): end-to-end on the real backend
- [ ] Checkpoint 2 (6:00): full differentiator flow

## Phase 10: Deployment
Status: LOCKED until Checkpoint 2 passes

- [ ] Railway backend, Vercel frontend, Supabase demo DB

## Phase 11: Demo Hardening
Status: LOCKED until deployment works

- [ ] Stretch items (only if green), freeze at 7:30, rehearse with the presenter
