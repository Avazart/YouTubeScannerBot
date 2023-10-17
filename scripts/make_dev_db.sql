BEGIN;

DELETE FROM public."TelegramChats";

INSERT INTO public."TelegramChats" 
       (original_id, type, title, user_name, first_name, last_name, is_creator, status) 
VALUES (-1001716179047, 'supergroup', 'AvazartTestGroup', 'AvazartTestGroup', NULL, NULL, NULL, 0);


INSERT INTO public."TelegramThreads" (id, original_id, original_chat_id, title) VALUES (1, 1900, -1001716179047, 'T1');
INSERT INTO public."TelegramThreads" (id, original_id, original_chat_id, title) VALUES (2, 1902, -1001716179047, 'T2');
INSERT INTO public."TelegramThreads" (id, original_id, original_chat_id, title) VALUES (3, 2028, -1001716179047, 'T3');
COMMIT;


