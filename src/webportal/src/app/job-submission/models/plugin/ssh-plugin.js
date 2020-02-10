/*
 * Copyright (c) Microsoft Corporation
 * All rights reserved.
 *
 * MIT License
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { get, isEmpty } from 'lodash';
import { removeEmptyProperties } from '../../utils/utils';
import { PAI_PLUGIN } from '../../utils/constants';

export class SSHPlugin {
  constructor(props) {
    const { jobssh, userssh, enable} = props;
    this.jobssh = jobssh || false;
    this.userssh = userssh || {};
    this.enable = enable || !(isEmpty(userssh)) || false;
  }

  static fromProtocol(extras) {
    const pluginBase = get(extras, PAI_PLUGIN, []);
    const sshPluginProtocol = pluginBase.find(
      plugin => plugin.plugin === 'ssh',
    );

    if (sshPluginProtocol === undefined) {
      return new SSHPlugin({});
    } else {
      const jobssh = get(sshPluginProtocol, 'parameters.jobssh', false);
      const userssh = get(sshPluginProtocol, 'parameters.userssh', {});
      const enable = get(sshPluginProtocol, 'parameters.enable', false) || !(isEmpty(userssh));

      return new SSHPlugin({
        ...sshPluginProtocol,
        jobssh: jobssh,
        userssh: userssh,
        enable: enable
      });
    }
  }

  convertToProtocolFormat() {
    return removeEmptyProperties({
      plugin: 'ssh',
      parameters: {
        jobssh: this.jobssh,
        userssh: this.userssh,
        enable: this.enable,
      },
    });
  }

  getUserSshValue() {
    return get(this.userssh, 'value');
  }
}