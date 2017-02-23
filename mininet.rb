#
# Copyright (c) 2006-2009 National ICT Australia (NICTA), Australia
#
# Copyright (c) 2004-2009 WINLAB, Rutgers University, USA
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# = ath9k.rb
#
# == Description
#
# This file defines the class Ath9kDevice which is a sub-class of
# WirelessDevice.
#
require 'omf-resctl/omf_driver/wireless'

#
# This class represents an Ath9kDevice
#
class Mininet < WirelessDevice

  FREQUENCY= { 1 => '2412',
              2 => '2417',
              3 => '2422',
              4 => '2427',
              5 => '2432',
              6 => '2437',
              7 => '2442',
              8 => '2447',
              9 => '2452',
              10 => '2457',
              11 => '2462',
              12 => '2467',
              13 => '2472',
              14 => '2484',
              36 => '5180',
              40 => '5200',
              44 => '5220',
              48 => '5240',
              52 => '5260',
              56 => '5280',
              60 => '5300',
              64 => '5320',
              100 => '5500',
              104 => '5520',
              108 => '5540',
              112 => '5560',
              116 => '5580',
              120 => '5600',
              124 => '5620',
              128 => '5640',
              132 => '5660',
              136 => '5680',
              140 => '5700',
              149 => '5745',
              153 => '5765',
              157 => '5785',
              161 => '5805',
              165 => '5825' }

  def clean_app(name, fpid, fconf)
    begin
      f = File.open(fpid,'r')
      pid = nil
      f.each { |l| pid = l }
      debug "Stopping #{name} process at PID: #{pid}"
      clean = `kill -9 #{pid}`
      f.close
      clean = `rm -f #{fpid} #{fconf}`
    rescue Exception => ex
      debug "Failed to clean #{name} and its related files '#{fpid}' and '#{fconf}'!"
    end
  end

  def unload
    super()
    case @mode
      when :master
        clean_app(@hostapd, @appid, @apconf)
      when :managed
        clean_app(@wpasup, @wpapid, @wpaconf)
    end
    @type = @mode = @channel = @frequency = @essid = nil
  end

   def initialize(logicalName, deviceName)
    super(nil, deviceName)
    @driver = 'dummy'
    @iw = 'iw'
    @hostapd = 'hostapd'
    @wpasup = 'wpa_supplicant'
    @apconf = "/tmp/hostapd.#{@deviceName}.conf"
    @appid = "/tmp/hostapd.#{@deviceName}.pid"
    @wpaconf = "/tmp/wpa.#{@deviceName}.conf"
    @wpapid = "/tmp/wpa.#{@deviceName}.pid"
    @type = @mode = @channel = @frequency = @essid = nil
  end
  


  def buildCmd
    #mininet takes care of the initialization of modality
    return nil
  end

  #
  # Return the specific command required to configure a given property of this
  # device. When a property does not exist for this device, check if it does
  # for its super-class.
  #
  # - prop = the property to configure
  # - value = the value to configure that property to
  #
  def getConfigCmd(prop, value)

    @propertyList[prop.to_sym] = value
    case prop
      when 'type'
        if value == 'a' || value == 'b' || value == 'g' || value == 'n'
          @type = value
        else
          raise "Unknown type. Should be 'a', 'b', 'g', or 'n'"
        end
        return buildCmd

      when "mode"
        @mode = case
          when value.downcase == 'master' then :master
          when value.downcase == 'managed' then :managed
          when value.downcase == 'ad-hoc' then :adhoc
          when value.downcase == 'adhoc' then :adhoc
          when value.downcase == 'monitor' then :monitor
          else
            raise "Unknown mode '#{value}'. Should be 'master', 'managed', "+
                  "'adhoc', or monitor."
        end
        return buildCmd

      when "essid"
        @essid = value
        return "iwconfig #{@deviceName} essid #{value}" 

      when "rts"
        return buildCmd

     when "rate"
        @rate = value
        return "iwconfig #{@deviceName} rate #{value}" 

      when "frequency"
        return buildCmd

     when "channel"
        @channel = value
        return "iwconfig #{@deviceName} channel #{value}" 

     when "tx_power"
        # Note: 'iw' support txpower setting only in latest version
        # however current version shipped with natty (0.9.19) does not
        # suppot that so for now we use 'iwconfig'
        return "iwconfig #{@deviceName} txpower #{value}"

    end
    super
  end

  def get_property_value(prop)
    # Note: for now we are returning values set by a CONFIGURE command
    # when refactoring the device handling scheme, we may want to query
    # the system here to find out the real value of the property
    result = super(prop)
    result = @propertyList[prop] if !result
    return result
  end



end
