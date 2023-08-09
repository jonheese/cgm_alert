--
-- Table structure for table `tbl_alert`
--

DROP TABLE IF EXISTS `tbl_alert`;
CREATE TABLE `tbl_alert` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `timestamp` int(11) NOT NULL,
  `status_id` bigint(20) unsigned NOT NULL,
  `uuid` varchar(37) NOT NULL,
  `is_acked` tinyint(1) NOT NULL DEFAULT '0',
  UNIQUE KEY `id` (`id`),
  UNIQUE KEY `timestamp_status_id` (`timestamp`,`status_id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;

--
-- Table structure for table `tbl_status`
--

DROP TABLE IF EXISTS `tbl_status`;
CREATE TABLE `tbl_status` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `status_name` varchar(16) NOT NULL,
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;

--
-- Dumping data for table `tbl_status`
--

INSERT INTO `tbl_status` VALUES (0,'Normal'),(1,'High'),(2,'Low'),(3,'Urgent Low'),(4,'Unknown');

--
-- View structure for view `view_alert`
--

DROP VIEW IF EXISTS `view_alert`*/;
CREATE VIEW `view_alert` AS
  SELECT
    `a`.`id` AS `id`,
    from_unixtime(`a`.`timestamp`) AS `timestamp`,
    `s`.`status_name` AS `status_name`,
    `a`.`uuid` AS `uuid`,
    `a`.`is_acked` AS `is_acked`
  FROM (
    `tbl_alert` `a` JOIN `tbl_status` `s`
    ON (`a`.`status_id` = `s`.`id`)
  )
);
