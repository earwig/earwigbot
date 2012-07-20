-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_afc_copyvios
-- ------------------------------------------------------
-- Server version       5.1.59

--
-- Table structure for table `cache`
--

DROP TABLE IF EXISTS `cache`;
CREATE TABLE `cache` (
  `cache_id` int(10) unsigned NOT NULL,
  `cache_hash` char(64) DEFAULT NULL,
  `cache_url` varchar(512) DEFAULT NULL,
  `cache_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `cache_queries` int(4) DEFAULT NULL,
  `cache_process_time` float DEFAULT NULL,
  PRIMARY KEY (`cache_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Table structure for table `processed`
--

DROP TABLE IF EXISTS `processed`;
CREATE TABLE `processed` (
  `page_id` int(10) unsigned NOT NULL,
  PRIMARY KEY (`page_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Dump completed on 2012-07-20 18:04:20
