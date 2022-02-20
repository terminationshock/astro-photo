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

        integer(4) :: indices(2)

        if (x0 < 0 .or. y0 < 0) then
            indices = maxloc(pixels)
            x = indices(1)
            y = indices(2)
        else
            x = x0 + 1.d0
            y = y0 + 1.d0
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
