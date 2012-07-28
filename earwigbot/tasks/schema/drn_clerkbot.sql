-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_drn_clerkbot
-- ------------------------------------------------------
-- Server version       5.1.59

CREATE DATABASE `u_earwig_drn_clerkbot`
  DEFAULT CHARACTER SET utf8
  DEFAULT COLLATE utf8_unicode_ci;

--
-- Table structure for table `case`
--

DROP TABLE IF EXISTS `case`;
CREATE TABLE `case` (
  `case_id` int(10) unsigned NOT NULL,
  `case_title` varchar(512) COLLATE utf8_unicode_ci DEFAULT NULL,
  `case_status` int(2) unsigned NOT NULL,
  PRIMARY KEY (`case_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- Dump completed on 2012-07-27 00:00:00
