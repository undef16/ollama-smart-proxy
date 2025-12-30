---
description: "Task list template for feature implementation"
---

# Tasks: Ollama Smart Proxy

**Input**: Design documents from `/specs/001/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included for key components.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Repository root for src/, tests/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python 3.12+ project with FastAPI and ollama dependencies
- [ ] T003 [P] Configure linting and formatting tools (black, flake8)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Setup global configuration in src/shared/config.py
- [ ] T005 [P] Implement Plugin Registry in src/shared/plugin_registry.py
- [ ] T006 [P] Create Ollama Client wrapper in src/shared/ollama_client.py
- [ ] T007 [P] Setup logging infrastructure in src/shared/logging.py
- [ ] T008 Create main.py entry point

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Chat Interaction (Priority: P1) 🎯 MVP

**Goal**: Enable basic chat requests with OpenAI-compatible API

**Independent Test**: Send POST /api/chat and verify response

### Tests for User Story 1

- [ ] T009 [P] [US1] Unit test for chat request parsing in tests/unit/test_chat.py
- [ ] T010 [P] [US1] Integration test for chat endpoint in tests/integration/test_chat_slice.py

### Implementation for User Story 1

- [ ] T011 [US1] Create chat slice router in src/slices/chat/router.py
- [ ] T012 [US1] Implement chat logic in src/slices/chat/logic.py (model extraction, forwarding)
- [ ] T013 [US1] Mount chat router in main.py

**Checkpoint**: US1 functional independently

---

## Phase 4: User Story 2 - Dynamic Model Loading (Priority: P1)

**Goal**: Support dynamic model loading based on requests

**Independent Test**: Request unloaded model, verify loading

### Implementation for User Story 2

- [ ] T014 [US2] Update chat logic to handle model loading in src/slices/chat/logic.py

**Checkpoint**: US1 and US2 work independently

---

## Phase 5: User Story 3 - Agent Activation via Slash Commands (Priority: P2)

**Goal**: Enable agent customization via slash commands

**Independent Test**: Send prompt with /example, verify agent activation

### Tests for User Story 3

- [ ] T015 [P] [US3] Unit test for agent chain execution in tests/unit/test_agent_chain.py

### Implementation for User Story 3

- [ ] T016 [US3] Implement slash command parsing in src/slices/chat/logic.py
- [ ] T017 [US3] Add agent chain execution in src/slices/chat/logic.py
- [ ] T018 [US3] Create example agent in src/plugins/example_agent/agent.py

---

## Phase 6: User Story 6 - Pass-Through Endpoints (Priority: P2)

**Goal**: Provide access to standard Ollama APIs

**Independent Test**: Call /api/tags, verify response

### Implementation for User Story 6

- [ ] T019 [US6] Create pass-through routers in src/slices/passthrough/router.py
- [ ] T020 [US6] Mount pass-through routers in main.py

---

## Phase 7: User Story 4 - Health Monitoring (Priority: P3)

**Goal**: Provide operational health checks

**Independent Test**: Call /health, verify status

### Implementation for User Story 4

- [ ] T021 [US4] Create health router in src/slices/health/router.py
- [ ] T022 [US4] Mount health router in main.py

---

## Phase 8: User Story 5 - Plugin Introspection (Priority: P3)

**Goal**: Allow inspection of loaded plugins

**Independent Test**: Call /plugins, verify list

### Implementation for User Story 5

- [ ] T023 [US5] Create plugins router in src/slices/plugins/router.py
- [ ] T024 [US5] Mount plugins router in main.py

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T025 [P] Add comprehensive unit tests in tests/unit/
- [ ] T026 Add error handling and logging across slices
- [ ] T027 Performance optimization and async improvements
- [ ] T028 Documentation updates
- [ ] T029 Run integration tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 completion
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 6 (P2)**: Can start after Foundational (Phase 2) - Independent
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Independent

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2 + 6
   - Developer C: User Story 3 + 4 + 5
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence