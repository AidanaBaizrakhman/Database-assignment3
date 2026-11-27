START TRANSACTION;

INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
  (1, 'Arman', 'Armanov', 'arman.armanov@example.com', 'Nazarbayev University', 'Kazakhstan', '+77011112233'),
  (2, 'Amina', 'Aminova', 'amina.aminova@example.com', 'Astana IT University', 'Kazakhstan', '+77022223344'),
  (3, 'Dana', 'Serikova', 'dana.serikova@example.com', 'Nazarbayev University', 'Kazakhstan', '+77033334455'),
  (4, 'Timur', 'Kassymov', 'timur.kassymov@example.com', 'KBTU', 'Kazakhstan', '+77044445566'),
  (5, 'Aliya', 'Nurlanova', 'aliya.nurlanova@example.com', 'Satbayev University', 'Kazakhstan', '+77055556677'),
  (6, 'Bauyrzhan', 'Ospanov', 'bauyrzhan.ospanov@example.com', 'L.N. Gumilyov Eurasian National University', 'Kazakhstan', '+77066667788'),
  (7, 'Madina', 'Zhaksylykova', 'madina.zhaksylykova@example.com', 'Al-Farabi Kazakh National University', 'Kazakhstan', '+77077778899'),
  (8, 'Nurlan', 'Abenov', 'nurlan.abenov@example.com', 'Astana IT University', 'Kazakhstan', '+77088889900'),
  (9, 'Elena', 'Petrova', 'elena.petrova@example.com', 'Novosibirsk State University', 'Russia', '+79131234567'),
  (10, 'John', 'Smith', 'john.smith@example.com', 'University of Edinburgh', 'United Kingdom', '+441312345678'),
  (11, 'Sofia', 'Garcia', 'sofia.garcia@example.com', 'Universidad de Granada', 'Spain', '+34958123456'),
  (12, 'Yerlan', 'Mukhanov', 'yerlan.mukhanov@example.com', 'Nazarbayev University', 'Kazakhstan', '+77012223344'),
  (13, 'Kamila', 'Ismailova', 'kamila.ismailova@example.com', 'Inha University in Tashkent', 'Uzbekistan', '+998901234567'),
  (14, 'Ruslan', 'Bekov', 'ruslan.bekov@example.com', 'AUCA', 'Kyrgyzstan', '+996555123456');

INSERT INTO author (author_id, orcid) VALUES
  (1, '0000-0001-1111-0001'),
  (2, '0000-0001-1111-0002'),
  (3, NULL),
  (4, '0000-0001-1111-0004'),
  (5, '0000-0001-1111-0005'),
  (9, '0000-0001-1111-0009'),
  (11, NULL),
  (12, '0000-0001-1111-0012'),
  (14, NULL);

INSERT INTO author_research_area (author_id, area_label) VALUES
  (1, 'Databases'),
  (2, 'Machine Learning'),
  (2, 'Human-Computer Interaction'),
  (3, 'Databases'),
  (4, 'Software Engineering'),
  (5, 'Machine Learning'),
  (9, 'Computer Vision'),
  (9, 'Machine Learning'),
  (11, 'Software Engineering'),
  (12, 'Databases'),
  (14, 'Networks');

INSERT INTO reviewer (reviewer_id, years_experience) VALUES
  (1, 5),
  (5, 2),
  (6, 8),
  (7, 4),
  (8, 1),
  (9, 6),
  (10, 10),
  (12, 3),
  (13, 0);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
  (1, 'Databases'),
  (1, 'Distributed Systems'),
  (5, 'Machine Learning'),
  (6, 'Databases'),
  (6, 'Data Mining'),
  (7, 'Software Engineering'),
  (7, 'Databases'),
  (8, 'Networks'),
  (9, 'Computer Vision'),
  (9, 'Machine Learning'),
  (10, 'Databases'),
  (10, 'Information Retrieval'),
  (12, 'Databases'),
  (13, 'Software Engineering');

INSERT INTO conference (conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) VALUES
  (1, 'Data and Big Computing Asia', 'DBCA-2026', 'Annual conference on data management and large-scale computing.', 'Astana', 'Kazakhstan', '2026-06-15', '2026-06-17', '2026-02-15', '2026-04-01'),
  (2, 'Silk Road Computing Conference', 'SRCC-2026', 'Software engineering and computer vision research in Central Asia.', 'Almaty', 'Kazakhstan', '2026-09-07', '2026-09-09', '2026-05-01', '2026-06-15'),
  (3, 'Central Asian AI Workshop', 'CAAI-2027', 'Workshop on foundations of artificial intelligence. Submissions not yet open.', 'Bishkek', 'Kyrgyzstan', '2027-05-20', '2027-05-21', '2027-02-01', '2027-03-20');

INSERT INTO conference_host (conference_id, host_name) VALUES
  (1, 'Nazarbayev University'),
  (1, 'Astana IT University'),
  (2, 'KBTU'),
  (2, 'Satbayev University'),
  (3, 'American University of Central Asia');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
  (1, 1),
  (1, 5),
  (1, 6),
  (1, 7),
  (1, 8),
  (1, 12),
  (1, 13),
  (2, 1),
  (2, 6),
  (2, 7),
  (2, 9),
  (2, 10),
  (3, 8),
  (3, 13);

INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
  (1, 1, 'Database Systems', 'Storage, indexing, query processing and transactions.', 'Databases', 6),
  (2, 1, 'Machine Learning for Data', 'Learning-based methods for data-intensive systems.', 'Machine Learning', 5),
  (3, 1, 'Blockchain Data Management', 'Ledger storage and verifiable queries.', 'Databases', 12),
  (4, 2, 'Software Engineering', 'Software quality, testing and maintenance.', 'Software Engineering', 7),
  (5, 2, 'Computer Vision', 'Image understanding and visual recognition.', 'Computer Vision', 9),
  (6, 3, 'AI Foundations', 'Theory and foundations of AI.', 'Machine Learning', 13);

INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
  (1, 1, 'Query Processing', '2026-06-15', '10:00:00', '11:30:00', 'A-101', 6),
  (2, 1, 'ML Systems', '2026-06-16', '14:00:00', '15:30:00', 'B-204', 5),
  (3, 1, 'Open Problems in Data Systems', '2026-06-17', '09:00:00', '10:00:00', 'A-102', 1),
  (4, 2, 'Software Quality', '2026-09-07', '11:00:00', '12:30:00', 'Hall 1', 7),
  (5, 2, 'Vision Applications', '2026-09-08', '15:00:00', '16:00:00', 'Hall 2', 9);

INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
  (1, 1, 'Adaptive Indexing for Hybrid Workloads', 'We present an adaptive indexing scheme that reorganizes data incrementally for mixed transactional and analytical workloads.', '2026-02-01', 'accepted', 1),
  (2, 1, 'Cost-Based Optimization with Learned Cardinalities', 'We replace histogram estimates with Machine Learning models to predict join cardinalities in a cost-based optimizer.', '2026-02-05', 'accepted', 1),
  (3, 2, 'Federated Learning on Edge Databases', 'This paper studies federated machine learning over embedded databases running on edge devices.', '2026-02-08', 'accepted', 2),
  (4, 2, 'Explainable Models for Tabular Data', 'We propose an explanation method for gradient-boosted models trained on relational tables.', '2026-02-10', 'accepted', NULL),
  (5, 1, 'Transaction Isolation in Cloud-Native Stores', 'We measure isolation anomalies in three cloud-native key-value stores under network partitions.', '2026-02-11', 'rejected', NULL),
  (6, 2, 'Privacy-Preserving Recommendation', 'A differentially private recommender built on top of a column store.', '2026-02-12', 'under review', NULL),
  (7, 1, 'Schema Evolution in Practice', 'An empirical study of schema changes in open-source web applications.', '2026-02-14', 'submitted', NULL),
  (8, 2, 'Learning Rate Schedules Revisited', 'We revisit warm-up and decay schedules for training models on database logs.', '2026-02-03', 'withdrawn', NULL),
  (9, 1, 'Graph Queries over Knowledge Bases', 'A rewriting technique for recursive graph queries over large knowledge bases.', '2026-02-06', 'withdrawn', NULL),
  (10, 4, 'Static Analysis for Microservices', 'A static analysis that detects broken API contracts between microservices.', '2026-04-10', 'accepted', 4),
  (11, 4, 'Test Flakiness Prediction', 'We predict flaky tests from execution traces using MACHINE LEARNING classifiers.', '2026-04-15', 'rejected', NULL),
  (12, 5, 'Lightweight Object Detection for Drones', 'A compact detector for real-time object detection on drone hardware.', '2026-04-20', 'withdrawn', NULL),
  (13, 5, 'Medical Image Segmentation with Few Labels', 'A semi-supervised segmentation method for medical scans with few annotations.', '2026-04-25', 'under review', NULL);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
  (1, 'indexing'),
  (1, 'HTAP'),
  (2, 'query optimization'),
  (2, 'cardinality estimation'),
  (2, 'machine learning'),
  (3, 'federated learning'),
  (3, 'edge computing'),
  (4, 'explainability'),
  (4, 'tabular data'),
  (5, 'transactions'),
  (5, 'isolation'),
  (5, 'cloud'),
  (6, 'privacy'),
  (6, 'recommender systems'),
  (7, 'schema evolution'),
  (7, 'empirical study'),
  (8, 'optimization'),
  (8, 'training'),
  (9, 'graph queries'),
  (9, 'knowledge bases'),
  (10, 'static analysis'),
  (10, 'microservices'),
  (11, 'software testing'),
  (11, 'flaky tests'),
  (12, 'object detection'),
  (12, 'drones'),
  (13, 'segmentation'),
  (13, 'medical imaging');

INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
  (1, 3, 1, TRUE),
  (1, 12, 2, FALSE),
  (2, 12, 1, TRUE),
  (2, 3, 2, FALSE),
  (2, 5, 3, FALSE),
  (3, 5, 1, TRUE),
  (3, 2, 2, FALSE),
  (4, 2, 1, TRUE),
  (4, 9, 2, FALSE),
  (5, 1, 1, TRUE),
  (5, 14, 2, FALSE),
  (6, 9, 1, TRUE),
  (7, 4, 1, TRUE),
  (8, 2, 1, TRUE),
  (8, 11, 2, FALSE),
  (9, 2, 1, TRUE),
  (10, 11, 1, TRUE),
  (10, 4, 2, FALSE),
  (11, 4, 1, TRUE),
  (11, 14, 2, FALSE),
  (12, 9, 1, TRUE),
  (12, 2, 2, FALSE),
  (13, 9, 1, TRUE),
  (13, 1, 2, FALSE);

INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
  (1, 1, '/storage/papers/1/v1.pdf', '2026-02-01 10:15:00', NULL),
  (1, 2, '/storage/papers/1/v2.pdf', '2026-05-10 18:00:00', 'Camera-ready version'),
  (2, 1, '/storage/papers/2/v1.pdf', '2026-02-05 09:00:00', NULL),
  (3, 1, '/storage/papers/3/v1.pdf', '2026-02-08 11:20:00', NULL),
  (3, 2, '/storage/papers/3/v2.pdf', '2026-02-14 23:10:00', 'Fixed figures before deadline'),
  (3, 3, '/storage/papers/3/v3.pdf', '2026-05-12 16:45:00', 'Camera-ready version'),
  (4, 1, '/storage/papers/4/v1.pdf', '2026-02-10 14:00:00', NULL),
  (5, 1, '/storage/papers/5/v1.pdf', '2026-02-11 08:30:00', NULL),
  (6, 1, '/storage/papers/6/v1.pdf', '2026-02-12 12:00:00', NULL),
  (6, 2, '/storage/papers/6/v2.pdf', '2026-02-15 20:00:00', 'Added experiments'),
  (7, 1, '/storage/papers/7/v1.pdf', '2026-02-14 17:40:00', NULL),
  (8, 1, '/storage/papers/8/v1.pdf', '2026-02-03 10:00:00', NULL),
  (8, 2, '/storage/papers/8/v2.pdf', '2026-02-09 10:00:00', 'Typo fixes'),
  (9, 1, '/storage/papers/9/v1.pdf', '2026-02-06 15:30:00', NULL),
  (10, 1, '/storage/papers/10/v1.pdf', '2026-04-10 09:00:00', NULL),
  (10, 3, '/storage/papers/10/v3.pdf', '2026-07-20 12:00:00', 'Camera-ready version (v2 was discarded)'),
  (11, 1, '/storage/papers/11/v1.pdf', '2026-04-15 10:30:00', NULL),
  (12, 1, '/storage/papers/12/v1.pdf', '2026-04-20 13:00:00', NULL),
  (13, 1, '/storage/papers/13/v1.pdf', '2026-04-25 19:00:00', NULL);

INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments, review_submission_date) VALUES
  (1, 1, 6, 5, 'accept', 'Clear motivation and convincing experiments.', NULL, '2026-03-10'),
  (2, 1, 7, 4, 'accept', 'Solid work. The related work section could be extended.', NULL, '2026-03-12'),
  (3, 2, 6, 4, 'accept', 'Good idea, please add a runtime overhead analysis.', NULL, '2026-03-11'),
  (4, 2, 1, 5, 'accept', 'Strong results on standard benchmarks.', 'Best paper candidate.', '2026-03-15'),
  (5, 3, 6, 4, 'accept', 'Interesting setting, well-written.', NULL, '2026-03-13'),
  (6, 3, 12, 4, 'accept', 'Reasonable evaluation on real devices.', NULL, '2026-03-18'),
  (7, 4, 7, 4, 'accept', 'Useful method with a clear user study.', NULL, '2026-03-20'),
  (8, 5, 6, 2, 'reject', 'The experimental setup does not support the claims.', NULL, '2026-03-14'),
  (9, 5, 13, 1, 'reject', 'Results are not reproducible from the description.', 'Possible overlap with a prior paper.', '2026-03-22'),
  (10, 6, 5, 3, 'accept', 'Promising but the privacy budget analysis needs work.', NULL, '2026-03-25'),
  (11, 8, 1, 2, 'reject', 'Limited novelty compared to existing schedules.', NULL, '2026-02-20'),
  (12, 9, 7, 3, 'reject', 'The rewriting rules need a correctness proof.', NULL, '2026-02-25'),
  (13, 10, 10, 5, 'accept', 'Practical and well evaluated on industrial systems.', NULL, '2026-05-30'),
  (14, 10, 6, 4, 'accept', 'Good tool support, minor presentation issues.', NULL, '2026-06-02'),
  (15, 11, 10, 2, 'reject', 'Dataset is too small to support the conclusions.', NULL, '2026-06-01'),
  (16, 11, 7, 2, 'reject', 'Baselines are missing.', NULL, '2026-06-05'),
  (17, 12, 10, 3, 'reject', 'Accuracy drop is not discussed.', NULL, '2026-05-28'),
  (18, 13, 6, 4, 'accept', 'Convincing results with very few labels.', NULL, '2026-06-10');

COMMIT;