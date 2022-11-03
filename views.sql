DROP VIEW IF EXISTS ForwardingView;

CREATE VIEW ForwardingView AS
    SELECT Forwarding.enabled,
           YouTubeChannels.title AS yt_channel_title,
           TelegramObjects.user_name AS tg_user_name,
           TelegramObjects.title AS tg_title,
           TelegramObjects.type  AS tg_type,
           YouTubeChannels.id AS yt_id,
           TelegramObjects.id AS tg_id,
           YouTubeChannels.canonical_base_url
      FROM Forwarding
           LEFT JOIN
           YouTubeChannels,
           TelegramObjects ON Forwarding.youtube_channel_id == YouTubeChannels.id AND
                              Forwarding.telegram_id == TelegramObjects.id
     ORDER BY YouTubeChannels.title;


DROP VIEW IF EXISTS YouTubeVideoView;

CREATE VIEW YouTubeVideoView AS
    SELECT YouTubeChannels.title AS yt_channel_title,
           YouTubeVideo.id AS yt_video_id,
           YouTubeVideo.title AS yt_video_title,
           YouTubeVideo.scan_time,
           YouTubeVideo.time_ago,
           YouTubeVideo.creation_time
      FROM YouTubeVideo
           LEFT JOIN
           YouTubeChannels ON YouTubeChannels.id == YouTubeVideo.channel_id
     ORDER BY YouTubeVideo.creation_time DESC;