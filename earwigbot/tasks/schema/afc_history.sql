-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_afc_history
-- ------------------------------------------------------
-- Server version       5.1.59

CREATE DATABASE `u_earwig_afc_history`
  DEFAULT CHARACTER SET utf8
  DEFAULT COLLATE utf8_unicode_ci;

--
-- Table structure for table `page`
--

DROP TABLE IF EXISTS `page`;
CREATE TABLE `page` (
  `page_id` int(10) unsigned NOT NULL,
  `page_date` varchar(50) COLLATE utf8_unicode_ci DEFAULT NULL,
  `page_status` tinyint(3) unsigned DEFAULT NULL,
  PRIMARY KEY (`page_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- Dump completed on 2012-07-20 20:20:39
