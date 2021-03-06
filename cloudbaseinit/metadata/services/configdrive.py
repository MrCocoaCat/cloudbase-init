# Copyright 2012 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import shutil

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit import constant
from cloudbaseinit import exception
from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import baseopenstackservice
from cloudbaseinit.metadata.services.osconfigdrive import factory

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)
#"vfat",    # Visible device (with partition table).
#"iso",    # "Raw" format containing ISO bytes.
CD_TYPES = constant.CD_TYPES


# Look into optical devices. Only an ISO format could be
# used here (vfat ignored).
# "cdrom",
# Search through physical disks for raw ISO content or vfat filesystems
# containing configuration drive's content.
# "hdd",
# Search through partitions for raw ISO content or through volumes
# containing configuration drive's content.
# "partition",
CD_LOCATIONS = constant.CD_LOCATIONS

# BaseOpenStackService

class ConfigDriveService(baseopenstackservice.BaseOpenStackService):

    def __init__(self):
        super(ConfigDriveService, self).__init__()
        self._metadata_path = None
    # 私有函数，预处理
    def _preprocess_options(self):
        self._searched_types = set(CONF.config_drive.types)
        self._searched_locations = set(CONF.config_drive.locations)

        # Deprecation backward compatibility.
        if CONF.config_drive.raw_hdd:
            self._searched_types.add("iso")
            self._searched_locations.add("hdd")
        if CONF.config_drive.cdrom:
            self._searched_types.add("iso")
            self._searched_locations.add("cdrom")
        if CONF.config_drive.vfat:
            self._searched_types.add("vfat")
            self._searched_locations.add("hdd")

        # Check for invalid option values.
        if self._searched_types | CD_TYPES != CD_TYPES:
            raise exception.CloudbaseInitException(
                "Invalid Config Drive types %s", self._searched_types)
        if self._searched_locations | CD_LOCATIONS != CD_LOCATIONS:
            raise exception.CloudbaseInitException(
                "Invalid Config Drive locations %s", self._searched_locations)

    def load(self):
        super(ConfigDriveService, self).load()
        # 调用预处理函数，判断路径设置是否正确
        self._preprocess_options()
        # 获取对应平台的驱动，即使用WindowsConfigDriveManager 类进行配置
        self._mgr = factory.get_config_drive_manager()
        # 找到后已将配置信息 copy 至 target_path 中
        found = self._mgr.get_config_drive_files(
            searched_types=self._searched_types,
            searched_locations=self._searched_locations)

        if found:
            # target_path 为一随机路径
            self._metadata_path = self._mgr.target_path
            LOG.debug('Metadata copied to folder: %r', self._metadata_path)
        return found

    def _get_data(self, path):
        # path.normpath规范化路径
        norm_path = os.path.normpath(os.path.join(self._metadata_path, path))
        try:
            # rb 以二进制格式打开一个文件用于只读。文件指针将会放在文件的开头。这是默认模式
            with open(norm_path, 'rb') as stream:
                # 读取整个文件
                return stream.read()
        except IOError:
            raise base.NotExistingMetadataException()

    def cleanup(self):
        LOG.debug('Deleting metadata folder: %r', self._mgr.target_path)
        shutil.rmtree(self._mgr.target_path, ignore_errors=True)
        self._metadata_path = None
