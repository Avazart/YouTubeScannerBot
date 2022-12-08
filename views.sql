DROP VIEW IF EXISTS ForwardingView;

CREATE VIEW ForwardingView AS
    SELECT YouTubeChannels.title AS yt_channel_title,
           TelegramObjects.user_name AS tg_user_name,
           TelegramObjects.title AS tg_title,
           TelegramObjects.type  AS tg_type,
           YouTubeChannels.id AS yt_id,
           TelegramObjects.chat_id AS tg_id,
           TelegramObjects.thread_id AS tg_thread_id,
           YouTubeChannels.canonical_base_url
      FROM Forwarding
           LEFT JOIN
           YouTubeChannels,
           TelegramObjects ON Forwarding.youtube_channel_id == YouTubeChannels.id AND
                              Forwarding.telegram_chat_id == TelegramObjects.chat_id AND
                              (Forwarding.telegram_thread_id == TelegramObjects.thread_id OR
                               (Forwarding.telegram_thread_id IS NULL AND
                                TelegramObjects.thread_id IS NULL)
                              )

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


CREATE VIEW ChannelsAndTags AS
    SELECT YouTubeChannels.id,
           YouTubeChannels.title,
           tags
      FROM YouTubeChannels
           JOIN
           (
               SELECT YouTubeChannelTags.channel_id AS channel_id,
                      GROUP_CONCAT(Tags.name) AS tags
                 FROM YouTubeChannelTags
                      JOIN
                      Tags ON YouTubeChannelTags.tag_id = Tags.id
                GROUP BY YouTubeChannelTags.channel_id
           )
           ON channel_id == YouTubeChannels.id;