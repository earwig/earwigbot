-- MySQL dump 10.13  Distrib 5.5.12, for solaris10 (i386)
--
-- Host: sql    Database: u_earwig_afc_statistics
-- ------------------------------------------------------
-- Server version       5.1.59

--
-- Table structure for table `chart`
--

DROP TABLE IF EXISTS `chart`;
CREATE TABLE `chart` (
  `chart_id` tinyint(3) unsigned NOT NULL AUTO_INCREMENT,
  `chart_title` varchar(255) DEFAULT NULL,
  `chart_special_title` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`chart_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

--
-- Dumping data for table `chart`
--

LOCK TABLES `chart` WRITE;
INSERT INTO `chart` VALUES
(1,'Pending submissions','Submitted'),
(3,'Being reviewed','Reviewer'),
(4,'Recently accepted','Accepted'),
(5,'Recently declined','Declined'),
(6,'Misplaced submissions','Created');
UNLOCK TABLES;

--
-- Table structure for table `row`
--

DROP TABLE IF EXISTS `row`;
CREATE TABLE `row` (
  `row_id` int(10) unsigned NOT NULL,
  `row_chart` tinyint(3) unsigned DEFAULT NULL,
  PRIMARY KEY (`row_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Table structure for table `page`
--

DROP TABLE IF EXISTS `page`;
CREATE TABLE `page` (
  `page_id` int(10) unsigned NOT NULL,
  `page_status` varchar(16) DEFAULT NULL,
  `page_title` varchar(512) DEFAULT NULL,
  `page_short` varchar(512) DEFAULT NULL,
  `page_size` varchar(16) DEFAULT NULL,
  `page_notes` tinytext,
  `page_modify_user` varchar(255) DEFAULT NULL,
  `page_modify_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `page_modify_oldid` int(10) unsigned DEFAULT NULL,
  `page_special_user` varchar(255) DEFAULT NULL,
  `page_special_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `page_special_oldid` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`page_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Dump completed on 2012-07-20 17:57:36
