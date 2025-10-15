'use client';

import * as React from 'react';
import { styled } from '@mui/material/styles';
import Divider, { dividerClasses } from '@mui/material/Divider';
import Menu from '@mui/material/Menu';
import MuiMenuItem from '@mui/material/MenuItem';
import { paperClasses } from '@mui/material/Paper';
import { listClasses } from '@mui/material/List';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon, { listItemIconClasses } from '@mui/material/ListItemIcon';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import AccountCircleRoundedIcon from '@mui/icons-material/AccountCircleRounded';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';
import MenuButton from './MenuButton';
import AccountManagementDialog from './AccountManagementDialog';
import { createClient } from '@utils/supabase/client';

const MenuItem = styled(MuiMenuItem)({
  margin: '2px 0',
});

interface OptionsMenuProps {
  onUserDataUpdate?: () => void;
}

export default function OptionsMenu({ onUserDataUpdate }: OptionsMenuProps) {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [accountDialogOpen, setAccountDialogOpen] = React.useState(false);
  const open = Boolean(anchorEl);
  const supabase = createClient();

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleMyAccount = () => {
    setAccountDialogOpen(true);
    handleClose();
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      // Redirect will be handled by middleware
      window.location.href = '/sign-in';
    } catch (error) {
      console.error('Error logging out:', error);
    }
    handleClose();
  };

  const handleAccountUpdate = () => {
    if (onUserDataUpdate) {
      onUserDataUpdate();
    }
  };

  return (
    <React.Fragment>
      <MenuButton
        aria-label="Open menu"
        onClick={handleClick}
        sx={{ borderColor: 'transparent' }}
      >
        <MoreVertRoundedIcon />
      </MenuButton>
      <Menu
        anchorEl={anchorEl}
        id="menu"
        open={open}
        onClose={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        sx={{
          [`& .${listClasses.root}`]: {
            padding: '4px',
          },
          [`& .${paperClasses.root}`]: {
            padding: 0,
          },
          [`& .${dividerClasses.root}`]: {
            margin: '4px -4px',
          },
        }}
      >
        <MenuItem onClick={handleMyAccount}>
          <ListItemIcon>
            <AccountCircleRoundedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>My Account</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={handleLogout}
          sx={{
            [`& .${listItemIconClasses.root}`]: {
              ml: 'auto',
              minWidth: 0,
            },
          }}
        >
          <ListItemText>Logout</ListItemText>
          <ListItemIcon>
            <LogoutRoundedIcon fontSize="small" />
          </ListItemIcon>
        </MenuItem>
      </Menu>

      <AccountManagementDialog
        open={accountDialogOpen}
        onClose={() => setAccountDialogOpen(false)}
        onUserUpdate={handleAccountUpdate}
      />
    </React.Fragment>
  );
}
