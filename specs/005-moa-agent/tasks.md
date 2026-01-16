# Tasks: MoA Agent

**Input**: Design documents from `/specs/005-moa-agent/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit tests for each stage as specified in requirements

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Plugin structure: `src/plugins/moa/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic plugin structure

- [ ] T001 Create plugin directory structure at src/plugins/moa/
- [ ] T002 Create __init__.py in src/plugins/moa/
- [ ] T003 Create config.json template in src/plugins/moa/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement MoAAgent class inheriting from BaseAgent in src/plugins/moa/agent.py
- [ ] T005 Add configuration loading for environment variables and config.json
- [ ] T007 Set up async query infrastructure using proxy's Ollama client
- [ ] T008 Add error handling and logging framework for MoA operations

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enhanced Answer Quality with MoA (Priority: P1) 🎯 MVP

**Goal**: Enable users to get improved answers through multi-model consensus

**Independent Test**: Send /moa query and verify synthesized response is returned

### Tests for User Story 1 ⚠️

- [ ] T009 [P] [US1] Unit test for collect_responses function in tests/unit/plugins/moa/test_agent.py
- [ ] T010 [P] [US1] Unit test for collect_rankings function in tests/unit/plugins/moa/test_agent.py
- [ ] T011 [P] [US1] Unit test for synthesize_final function in tests/unit/plugins/moa/test_agent.py
- [ ] T012 [US1] Integration test for full MoA workflow in tests/integration/test_moa_agent.py

### Implementation for User Story 1

- [ ] T013 [US1] Implement collect_responses function for parallel model queries
- [ ] T014 [US1] Implement collect_rankings function with anonymization and parsing
- [ ] T015 [US1] Implement synthesize_final function for chairman model synthesis
- [ ] T016 [US1] Add ranking_prompt template for peer evaluation
- [ ] T017 [US1] Add chairman_prompt template for final synthesis
- [ ] T018 [US1] Integrate all stages in on_request method
- [ ] T019 [US1] Format final response as OpenAI-compatible chat completion

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Configurable Model Selection (Priority: P2)

**Goal**: Allow administrators to configure which models participate in MoA

**Independent Test**: Change model configurations and verify different models are used

### Tests for User Story 2 ⚠️

- [ ] T020 [P] [US2] Unit test for model configuration loading in tests/unit/plugins/moa/test_config.py
- [ ] T021 [US2] Integration test for model selection in tests/integration/test_moa_config.py

### Implementation for User Story 2

- [ ] T022 [US2] Implement get_moa_models() method for configurable model list
- [ ] T023 [US2] Implement get_chairman_model() method for chairman selection
- [ ] T024 [US2] Add environment variable support for OLLAMA_MoA_MODELS
- [ ] T025 [US2] Add environment variable support for OLLAMA_CHAIRMAN_MODEL
- [ ] T026 [US2] Add validation for model availability and limits

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Fallback Handling (Priority: P3)

**Goal**: Ensure system gracefully handles failures and provides responses

**Independent Test**: Simulate model failures and verify fallback responses

### Tests for User Story 3 ⚠️

- [ ] T027 [P] [US3] Unit test for failure handling in tests/unit/plugins/moa/test_fallbacks.py
- [ ] T028 [US3] Integration test for fallback scenarios in tests/integration/test_moa_fallbacks.py

### Implementation for User Story 3

- [ ] T029 [US3] Implement model failure exclusion in collect_responses
- [ ] T030 [US3] Add chairman model fallback to top-ranked response
- [ ] T031 [US3] Implement timeout handling for individual queries
- [ ] T032 [US3] Add graceful error messages for complete MoA failures

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T033 [P] Add comprehensive logging for MoA metrics and debugging
- [ ] T034 Add performance monitoring and timeout configuration
- [ ] T035 [P] Documentation updates in README and deployment guides
- [ ] T036 Code cleanup and add type hints throughout
- [ ] T037 [P] Additional unit tests for edge cases in tests/unit/plugins/moa/
- [ ] T038 Run quickstart.md validation for setup instructions

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of other stories
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of other stories

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Core functions before integration
- Prompts before workflow integration
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
   - Developer B: User Story 2
   - Developer C: User Story 3
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
- Prompts are critical for MoA functionality - ensure ranking_prompt and chairman_prompt are properly implemented