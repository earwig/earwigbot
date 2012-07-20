-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_afc_history
-- ------------------------------------------------------
-- Server version       5.1.59

--
-- Table structure for table `page`
--

DROP TABLE IF EXISTS `page`;
CREATE TABLE `page` (
  `page_id` int(10) unsigned NOT NULL,
  `page_date` varchar(50) DEFAULT NULL,
  `page_status` tinyint(3) unsigned DEFAULT NULL,
  PRIMARY KEY (`page_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Dump completed on 2012-07-20 18:03:11
