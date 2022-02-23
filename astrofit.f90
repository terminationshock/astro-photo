! This file is part of AstroPhoto.
!
! AstroPhoto is free software: you can redistribute it and/or modify
! it under the terms of the GNU General Public License as published by
! the Free Software Foundation, either version 3 of the License, or
! (at your option) any later version.
!
! AstroPhoto is distributed in the hope that it will be useful,
! but WITHOUT ANY WARRANTY; without even the implied warranty of
! MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
! GNU General Public License for more details.
!
! You should have received a copy of the GNU General Public License
! along with AstroPhoto.  If not, see <http://www.gnu.org/licenses/>.

module astrofit
contains

    subroutine fit(nx, ny, pixels, x0, y0, x, y)
        implicit none
        integer(4), intent(in) :: nx, ny
        real(8), intent(in) :: pixels(nx,ny)
        real(8), intent(in) :: x0, y0
        real(8), intent(out) :: x, y

        call initial_guess(pixels, x0, y0, x, y)

        call find_cluster_center(pixels, x, y)

        x = x - 1.d0
        y = y - 1.d0
    end subroutine

    subroutine initial_guess(pixels, x0, y0, x, y)
        implicit none
        real(8), intent(in) :: pixels(:,:)
        real(8), intent(in) :: x0, y0
        real(8), intent(out) :: x, y

        integer(4), parameter :: delta = 50
        integer(4) :: indices(2), i0, j0, i1, j1, i2, j2

        if (x0 < 0 .or. y0 < 0) then
            indices = maxloc(pixels)
            x = real(indices(1))
            y = real(indices(2))
        else
            i0 = int(x0) + 1
            j0 = int(y0) + 1

            i1 = max(1, i0 - delta)
            j1 = max(1, j0 - delta)
            i2 = min(size(pixels, dim=1), i0 + delta)
            j2 = min(size(pixels, dim=2), j0 + delta)

            indices = maxloc(pixels(i1:i2,j1:j2))
            x = real(indices(1) + i1 - 1)
            y = real(indices(2) + j1 - 1)
        end if
    end subroutine

    subroutine find_cluster_center(pixels, x, y)
        implicit none
        real(8), intent(in) :: pixels(:,:)
        real(8), intent(inout) :: x, y

        real(8) :: limit, norm
        integer(4) :: i, j, i0, j0, nx, ny
        integer(4), allocatable :: cluster(:,:)

        nx = size(pixels, dim=1)
        ny = size(pixels, dim=2)
        i0 = int(x)
        j0 = int(y)

        if (i0 == 1 .or. i0 == nx .or. j0 == 1 .or. j0 == ny) then
            return
        end if

        limit = 200.d0

        allocate(cluster(nx,ny))
        cluster(:,:) = 0
        cluster(i0,j0) = 1
        cluster(i0-1,j0) = -1
        cluster(i0+1,j0) = -1
        cluster(i0,j0-1) = -1
        cluster(i0,j0+1) = -1

        do while (any(cluster < 0))
            do i = 1, nx
                do j = 1, ny
                    if (cluster(i,j) < 0) then
                        if (i > 1 .and. cluster(i-1,j) == 0) then
                            if (pixels(i-1,j) > limit) then
                                cluster(i-1,j) = -1
                            end if
                        end if
                        if (j > 1 .and. cluster(i,j-1) == 0) then
                            if (pixels(i,j-1) > limit) then
                                cluster(i,j-1) = -1
                            end if
                        end if
                        if (i < nx .and. cluster(i+1,j) == 0) then
                            if (pixels(i+1,j) > limit) then
                                cluster(i+1,j) = -1
                            end if
                        end if
                        if (j < ny .and. cluster(i,j+1) == 0) then
                            if (pixels(i,j+1) > limit) then
                                cluster(i,j+1) = -1
                            end if
                        end if
                        cluster(i,j) = 1
                    end if
                end do
            end do
        end do

        x = 0.d0
        y = 0.d0
        norm = 0.d0
        do i = 1, nx
            do j = 1, ny
                if (cluster(i,j) > 0) then
                    x = x + real(i) * pixels(i,j)
                    y = y + real(j) * pixels(i,j)
                    norm = norm + pixels(i,j)
                end if
            end do
        end do

        deallocate(cluster)

        x = x / norm
        y = y / norm

    end subroutine

end module
