-- phpMyAdmin SQL Dump
-- version 4.9.7
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2021-11-01 13:42:16
-- 服务器版本： 10.3.29-MariaDB
-- PHP 版本： 7.3.24

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 数据库： `nastool`
--

-- --------------------------------------------------------

--
-- 表的结构 `emby_media_log`
--

CREATE TABLE `emby_media_log` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `source` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `org_name` varchar(200) COLLATE utf8mb4_bin NOT NULL,
  `tmdbid` varchar(20) COLLATE utf8mb4_bin NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `type` varchar(30) COLLATE utf8mb4_bin NOT NULL,
  `year` varchar(4) COLLATE utf8mb4_bin NOT NULL,
  `season` varchar(500) COLLATE utf8mb4_bin NOT NULL,
  `episode` varchar(1000) COLLATE utf8mb4_bin NOT NULL,
  `filenum` int(5) NOT NULL,
  `filesize` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `path` varchar(1000) COLLATE utf8mb4_bin NOT NULL,
  `note` text COLLATE utf8mb4_bin NOT NULL,
  `time` datetime NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='Emby媒体日志';

-- --------------------------------------------------------

--
-- 表的结构 `emby_playback_log`
--

CREATE TABLE `emby_playback_log` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user` varchar(10) COLLATE utf8mb4_bin NOT NULL,
  `device` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `client` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `ip` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `address` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `time` datetime NOT NULL,
  `media` text COLLATE utf8mb4_bin NOT NULL,
  `op` varchar(20) COLLATE utf8mb4_bin NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='Emby播放日志';

-- --------------------------------------------------------

--
-- 表的结构 `message_log`
--

CREATE TABLE `message_log` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `type` varchar(20) COLLATE utf8mb4_bin NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `text` varchar(1000) COLLATE utf8mb4_bin NOT NULL,
  `time` datetime NOT NULL,
  `errcode` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `errmsg` varchar(1000) COLLATE utf8mb4_bin NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- --------------------------------------------------------

--
-- 表的结构 `system_log`
--

CREATE TABLE `system_log` (
  `id` int(10) NOT NULL,
  `type` varchar(20) NOT NULL,
  `name` varchar(50) NOT NULL,
  `text` longtext NOT NULL,
  `time` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- 转储表的索引
--

--
-- 表的索引 `emby_media_log`
--
ALTER TABLE `emby_media_log`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD KEY `INDX_TITLE` (`title`);

--
-- 表的索引 `emby_playback_log`
--
ALTER TABLE `emby_playback_log`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`);

--
-- 表的索引 `message_log`
--
ALTER TABLE `message_log`
  ADD UNIQUE KEY `id` (`id`);

--
-- 表的索引 `system_log`
--
ALTER TABLE `system_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `name` (`name`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `emby_media_log`
--
ALTER TABLE `emby_media_log`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `emby_playback_log`
--
ALTER TABLE `emby_playback_log`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `message_log`
--
ALTER TABLE `message_log`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `system_log`
--
ALTER TABLE `system_log`
  MODIFY `id` int(10) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
