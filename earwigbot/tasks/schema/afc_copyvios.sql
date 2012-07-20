-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_afc_copyvios
-- ------------------------------------------------------
-- Server version       5.1.59

CREATE DATABASE `u_earwig_afc_copyvios`
  DEFAULT CHARACTER SET utf8
  DEFAULT COLLATE utf8_unicode_ci;

--
-- Table structure for table `cache`
--

DROP TABLE IF EXISTS `cache`;
CREATE TABLE `cache` (
  `cache_id` int(10) unsigned NOT NULL,
  `cache_hash` char(64) COLLATE utf8_unicode_ci DEFAULT NULL,
  `cache_url` varchar(512) COLLATE utf8_unicode_ci DEFAULT NULL,
  `cache_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `cache_queries` int(4) DEFAULT NULL,
  `cache_process_time` float DEFAULT NULL,
  PRIMARY KEY (`cache_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Table structure for table `processed`
--

DROP TABLE IF EXISTS `processed`;
CREATE TABLE `processed` (
  `page_id` int(10) unsigned NOT NULL,
  PRIMARY KEY (`page_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- Dump completed on 2012-07-20 20:21:00
